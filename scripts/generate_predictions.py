"""
generate_predictions.py
Generates probabilistic predictions for all 72 group-stage matches of
the 2026 World Cup and writes data/predictions_seed.sql for Supabase seeding.

Algorithm: exact Poisson probabilities from ELO-style team strength.
"""

import json
from datetime import date
from pathlib import Path

from elo_probability import rounded_outcome_percentages, top_scoreline_percentages
from xi_matchups import (
    build_xi_profiles,
    matchup_adjusted_strengths,
    missing_xi_context,
    partial_xi_matchup_note,
    profile_xi_context,
    team_xi_context,
    xi_matchup_note,
)

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"

MATCHES_FILE  = DATA_DIR / "matches.json"
STRENGTHS_FILE = DATA_DIR / "team_strength_snapshots.json"
WEIGHTS_FILE  = DATA_DIR / "model_weights.json"
CONTEXT_FILE  = DATA_DIR / "match_context.json"
TEAMS_FILE    = DATA_DIR / "teams.json"
OUTPUT_SQL    = DATA_DIR / "predictions_seed.sql"

def match_probs(sa: float, sb: float, base_goals: float, n=None, elo_scale: float = 400, max_goals: int = 12,
                elo_lambda_scale=None, draw_bias: float = 0.0, parity_scale: float = 600.0):
    """
    Returns (pa, pd, pb) in 0–100 scale where pa + pd + pb == 100.00
    sa, sb: ELO-style strength scores for team A and team B.
    n is accepted for backward compatibility; direct predictions are exact.
    The calibration parameters (elo_lambda_scale, draw_bias, parity_scale)
    keep these probabilities consistent with the Monte Carlo simulator.
    """
    return rounded_outcome_percentages(sa, sb, base_goals, elo_scale, max_goals,
                                       elo_lambda_scale, draw_bias, parity_scale)


# ── Tag logic ─────────────────────────────────────────────────────────────────
def global_tag(pa: float, pd: float, pb: float, is_inaugural: bool) -> str:
    if is_inaugural:
        return "Partido Inaugural"
    diff    = abs(pa - pb)
    max_p   = max(pa, pb)
    if max_p >= 65 and diff >= 30:
        return "Favorito claro"
    if max_p >= 55 and diff >= 15:
        return "Ligero favorito"
    if diff < 7:
        return "Duelo parejo"
    if pd > 33:
        return "Empate probable"
    return "Partido abierto"


# ── SQL escaping ───────────────────────────────────────────────────────────────
def esc(text: str) -> str:
    """Escape single quotes for PostgreSQL string literals."""
    if not text:
        return ""
    return text.replace("'", "''")


def sql_str(value: str) -> str:
    """Wrap string in single quotes, or return NULL."""
    if value is None or value == "":
        return "NULL"
    return f"'{esc(value)}'"


# ── Load data ─────────────────────────────────────────────────────────────────
def match_context_key(match):
    group = match.get("group") or match.get("grupo")
    jornada = match.get("jornada") or match.get("matchday")
    team_a = match.get("home_team") or match.get("team_a")
    team_b = match.get("away_team") or match.get("team_b")
    return (group, int(jornada), frozenset((team_a, team_b)))


def build_context_lookup(context_matches):
    by_id = {}
    by_group_round_pair = {}
    for ctx in context_matches:
        by_id[ctx["match_id"]] = ctx
        by_group_round_pair[match_context_key(ctx)] = ctx
    return by_id, by_group_round_pair


def find_context_for_match(match, ctx_by_id, ctx_by_group_round_pair):
    ctx = ctx_by_id.get(match["match_id"])
    if ctx:
        return ctx
    return ctx_by_group_round_pair.get(match_context_key(match), {})


def context_for_team(ctx, team_code):
    if not ctx:
        return {}
    if ctx.get("team_a") == team_code:
        return ctx.get("team_a_context", {}) or {}
    if ctx.get("team_b") == team_code:
        return ctx.get("team_b_context", {}) or {}
    return {}


def build_group_fixture_index(matches):
    groups = {}
    teams = {}
    for match in matches:
        group = match["group"]
        groups.setdefault(group, []).append(match)
        for code in (match["home_team"], match["away_team"]):
            teams.setdefault(code, []).append(match)

    def sort_key(match):
        return (
            int(match.get("jornada", 0)),
            str(match.get("date") or ""),
            int(match.get("match_number", 0)),
        )

    for group in groups:
        groups[group].sort(key=sort_key)
    for team in teams:
        teams[team].sort(key=sort_key)

    return {"groups": groups, "teams": teams}


def parse_match_date(match):
    raw = match.get("date") if match else None
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def opponent_name(match, team_code):
    if not match:
        return "por definir"
    if match.get("home_team") == team_code:
        return match.get("away_name") or match.get("away_team", "").upper()
    return match.get("home_name") or match.get("home_team", "").upper()


def neighbor_match(team_code, current_match, fixture_index, offset):
    schedule = fixture_index["teams"].get(team_code, [])
    current_id = current_match["match_id"]
    for index, match in enumerate(schedule):
        if match["match_id"] == current_id:
            target = index + offset
            if 0 <= target < len(schedule):
                return schedule[target]
            return None
    return None


def days_between(a_match, b_match):
    a_date = parse_match_date(a_match)
    b_date = parse_match_date(b_match)
    if not a_date or not b_date:
        return None
    return abs((b_date - a_date).days)


def rest_phrase(days_a, days_b):
    if days_a is None or days_b is None:
        return ""
    if days_a == days_b:
        return f" Ambos tienen {days_a} dias de margen."
    return f" El descanso tambien pesa: {days_a} dias para el local y {days_b} para el visitante."


def build_calendar_note(match, fixture_index):
    jornada = int(match.get("jornada", 0))
    group = match.get("group", "")
    team_a = match["home_team"]
    team_b = match["away_team"]
    name_a = match.get("home_name") or team_a.upper()
    name_b = match.get("away_name") or team_b.upper()

    if jornada == 1:
        next_a = neighbor_match(team_a, match, fixture_index, 1)
        next_b = neighbor_match(team_b, match, fixture_index, 1)
        days_a = days_between(match, next_a)
        days_b = days_between(match, next_b)
        return (
            f"Calendario: el debut define el margen inicial del Grupo {group}; "
            f"{name_a} luego enfrenta a {opponent_name(next_a, team_a)} y "
            f"{name_b} a {opponent_name(next_b, team_b)}, asi que sumar aqui reduce "
            f"la urgencia de la segunda jornada."
            + rest_phrase(days_a, days_b)
        )

    if jornada == 2:
        next_a = neighbor_match(team_a, match, fixture_index, 1)
        next_b = neighbor_match(team_b, match, fixture_index, 1)
        days_a = days_between(match, next_a)
        days_b = days_between(match, next_b)
        return (
            f"Calendario: en segunda jornada pesa el resultado de la J1; "
            f"{name_a} cierra la J3 contra {opponent_name(next_a, team_a)} y "
            f"{name_b} contra {opponent_name(next_b, team_b)}, por lo que el riesgo "
            f"del partido cambia segun los puntos ya sumados."
            + rest_phrase(days_a, days_b)
        )

    return (
        f"Calendario: cierre simultaneo del Grupo {group}; aqui importan el marcador, "
        f"la diferencia de goles y el corte de mejores terceros. Si un equipo llega "
        f"con ventaja puede gestionar piernas, pero si llega corto de puntos el partido "
        f"obliga a tomar mas riesgos."
    )


def pct_text(value):
    return f"{float(value):.1f}%"


def build_probability_note(match, pa, pd, pb):
    name_a = match.get("home_name") or match.get("team_a") or match.get("home_team", "").upper()
    name_b = match.get("away_name") or match.get("team_b") or match.get("away_team", "").upper()
    diff = abs(pa - pb)

    if diff < 7:
        return (
            f"El modelo ELO deja un cruce parejo: {name_a} {pct_text(pa)}, "
            f"empate {pct_text(pd)} y {name_b} {pct_text(pb)}."
        )

    favorite = name_a if pa > pb else name_b
    favorite_pct = pa if pa > pb else pb
    underdog = name_b if pa > pb else name_a
    underdog_pct = pb if pa > pb else pa
    return (
        f"El modelo ELO da ventaja a {favorite} ({pct_text(favorite_pct)}) "
        f"sobre {underdog} ({pct_text(underdog_pct)}), con empate en {pct_text(pd)}."
    )


def compose_prediction_explanation(base_explanation, probability_note, calendar_note):
    base = (base_explanation or "").strip()
    parts = []
    if base:
        parts.append(base)
    if probability_note:
        parts.append(probability_note)
    if calendar_note:
        parts.append(calendar_note)
    return " ".join(part for part in parts if part).strip()


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    matches   = load_json(MATCHES_FILE)
    strengths = load_json(STRENGTHS_FILE)["teams"]
    weights   = load_json(WEIGHTS_FILE)
    ctx_data  = load_json(CONTEXT_FILE)
    teams_data = load_json(TEAMS_FILE)

    base_goals = weights["base_goals_per_team"]   # 1.3
    elo_scale = weights.get("elo_scale", 400)
    max_goals = weights.get("poisson_max_goals", 12)
    xi_matchup_weight = weights.get("xi_matchup_weight", 0.20)
    elo_lambda_scale = weights.get("elo_lambda_scale")
    draw_bias = weights.get("draw_bias", 0.0)
    parity_scale = weights.get("parity_scale", 600.0)
    xi_profiles = build_xi_profiles(teams_data)

    ctx_by_id, ctx_by_group_round_pair = build_context_lookup(ctx_data["matches"])
    fixture_index = build_group_fixture_index(matches)

    # Identify the inaugural match
    inaugural_id = None
    for ctx in ctx_data["matches"]:
        if ctx.get("inaugural"):
            inaugural_id = ctx["match_id"]
            break

    rows = []
    missing_teams = set()

    for match in matches:
        mid   = match["match_id"]
        team_a = match["home_team"]
        team_b = match["away_team"]

        # Strength scores (fall back to 1500 if team not found)
        if team_a not in strengths:
            missing_teams.add(team_a)
        if team_b not in strengths:
            missing_teams.add(team_b)

        sa = strengths.get(team_a, {}).get("strength_score", 1500.0)
        sb = strengths.get(team_b, {}).get("strength_score", 1500.0)

        effective_sa, effective_sb, xi_comparison = matchup_adjusted_strengths(
            team_a,
            team_b,
            sa,
            sb,
            xi_profiles,
            xi_matchup_weight=xi_matchup_weight,
        )

        pa, pd, pb = match_probs(effective_sa, effective_sb, base_goals, elo_scale=elo_scale, max_goals=max_goals,
                                 elo_lambda_scale=elo_lambda_scale, draw_bias=draw_bias, parity_scale=parity_scale)

        top_scorelines = top_scoreline_percentages(
            effective_sa, effective_sb, base_goals, elo_scale=elo_scale, max_goals=max_goals,
            elo_lambda_scale=elo_lambda_scale, draw_bias=draw_bias, parity_scale=parity_scale,
            top_n=5,
        )

        is_inaugural = (mid == inaugural_id)
        tag = global_tag(pa, pd, pb, is_inaugural)

        # Context fields
        ctx = find_context_for_match(match, ctx_by_id, ctx_by_group_round_pair)
        team_a_ctx_text = ""
        team_b_ctx_text = ""
        explanation     = ""
        if ctx:
            team_a_ctx_text = context_for_team(ctx, team_a).get("incentivo_competitivo", "") or ""
            team_b_ctx_text = context_for_team(ctx, team_b).get("incentivo_competitivo", "") or ""
            explanation     = ctx.get("prediccion_narrativa", "") or ""

        if xi_comparison:
            team_a_ctx_text = team_xi_context(xi_comparison["a"])
            team_b_ctx_text = team_xi_context(xi_comparison["b"])
            explanation = xi_matchup_note(match, xi_comparison)
        else:
            profile_a = xi_profiles.get(team_a)
            profile_b = xi_profiles.get(team_b)
            partial_note = partial_xi_matchup_note(match, team_a, team_b, xi_profiles)
            if partial_note:
                team_a_ctx_text = profile_xi_context(profile_a) if profile_a else missing_xi_context(match.get("home_name") or team_a.upper())
                team_b_ctx_text = profile_xi_context(profile_b) if profile_b else missing_xi_context(match.get("away_name") or team_b.upper())
                explanation = partial_note

        explanation = compose_prediction_explanation(
            explanation,
            build_probability_note(match, pa, pd, pb),
            build_calendar_note(match, fixture_index),
        )

        rows.append({
            "match_id":   mid,
            "group_code": match["group"],
            "matchday":   match["jornada"],
            "match_order": match["match_number"],
            "team_a":     team_a,
            "team_b":     team_b,
            "pa": pa,
            "pd": pd,
            "pb": pb,
            "tag": tag,
            "team_a_ctx": team_a_ctx_text,
            "team_b_ctx": team_b_ctx_text,
            "explanation": explanation,
            "top_scorelines": top_scorelines,
        })

    if missing_teams:
        print(f"WARNING — teams not found in strengths file: {missing_teams}")

    # ── Build SQL ─────────────────────────────────────────────────────────────
    lines = []
    lines.append("-- Auto-generated by scripts/generate_predictions.py")
    lines.append("-- 2026 FIFA World Cup — Group Stage Predictions (72 matches)")
    lines.append("")
    lines.append("TRUNCATE public.predictions RESTART IDENTITY;")
    lines.append("")
    lines.append("INSERT INTO public.predictions")
    lines.append("  (match_id, group_code, matchday, match_order, team_a, team_b,")
    lines.append("   team_a_win_probability, draw_probability, team_b_win_probability,")
    lines.append("   global_tag, team_a_context, team_b_context, explanation,")
    lines.append("   top_scorelines, is_premium, published, created_at, updated_at)")
    lines.append("VALUES")

    value_lines = []
    for row in rows:
        v = (
            f"  ({sql_str(row['match_id'])}, "
            f"{sql_str(row['group_code'])}, "
            f"{row['matchday']}, "
            f"{row['match_order']}, "
            f"{sql_str(row['team_a'])}, "
            f"{sql_str(row['team_b'])}, "
            f"{row['pa']}, "
            f"{row['pd']}, "
            f"{row['pb']}, "
            f"{sql_str(row['tag'])}, "
            f"{sql_str(row['team_a_ctx'])}, "
            f"{sql_str(row['team_b_ctx'])}, "
            f"{sql_str(row['explanation'])}, "
            f"{sql_str(json.dumps(row['top_scorelines'], separators=(',', ':')))}, "
            f"true, true, NOW(), NOW())"
        )
        value_lines.append(v)

    lines.append(",\n".join(value_lines) + ";")
    lines.append("")
    lines.append("-- Verify")
    lines.append("SELECT COUNT(*), MIN(group_code), MAX(group_code) FROM public.predictions;")

    sql_content = "\n".join(lines)

    with open(OUTPUT_SQL, "w", encoding="utf-8") as fh:
        fh.write(sql_content)

    print(f"Generated {len(rows)} rows -> {OUTPUT_SQL}")
    print("\nSample probabilities:")
    for r in rows[:5]:
        print(f"  {r['match_id']:35s}  A={r['pa']:5.2f}%  D={r['pd']:5.2f}%  B={r['pb']:5.2f}%  [{r['tag']}]")


if __name__ == "__main__":
    main()
