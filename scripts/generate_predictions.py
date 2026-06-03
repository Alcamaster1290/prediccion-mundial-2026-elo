"""
generate_predictions.py
Generates probabilistic predictions for all 72 group-stage matches of
the 2026 World Cup and writes data/predictions_seed.sql for Supabase seeding.

Algorithm: Poisson Monte Carlo (N=50000, seed=42)
"""

import json
import math
import random
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"

MATCHES_FILE  = DATA_DIR / "matches.json"
STRENGTHS_FILE = DATA_DIR / "team_strength_snapshots.json"
WEIGHTS_FILE  = DATA_DIR / "model_weights.json"
CONTEXT_FILE  = DATA_DIR / "match_context.json"
OUTPUT_SQL    = DATA_DIR / "predictions_seed.sql"

# ── Reproducibility ────────────────────────────────────────────────────────────
random.seed(42)
N_SIMULATIONS = 50_000


# ── Poisson helpers ────────────────────────────────────────────────────────────
def poisson_goals(lam: float) -> int:
    """Knuth algorithm for Poisson-distributed integer."""
    L = math.exp(-max(lam, 0.01))
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def match_probs(sa: float, sb: float, base_goals: float, n: int = N_SIMULATIONS):
    """
    Returns (pa, pd, pb) in 0–100 scale where pa + pd + pb == 100.00
    sa, sb: ELO-style strength scores for team A and team B.
    """
    factor = 10 ** ((sa - sb) / 800)
    la = base_goals * factor
    lb = base_goals / factor

    wins_a = wins_b = draws = 0
    for _ in range(n):
        ga = poisson_goals(la)
        gb = poisson_goals(lb)
        if ga > gb:
            wins_a += 1
        elif ga == gb:
            draws += 1
        else:
            wins_b += 1

    pa = round(100 * wins_a / n, 2)
    pd = round(100 * draws  / n, 2)
    pb = round(100.00 - pa - pd, 2)   # guarantees exact sum = 100
    return pa, pd, pb


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
def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    matches   = load_json(MATCHES_FILE)
    strengths = load_json(STRENGTHS_FILE)["teams"]
    weights   = load_json(WEIGHTS_FILE)
    ctx_data  = load_json(CONTEXT_FILE)

    base_goals = weights["base_goals_per_team"]   # 1.3

    # Build context lookup: match_id → context dict
    ctx_lookup = {m["match_id"]: m for m in ctx_data["matches"]}

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

        pa, pd, pb = match_probs(sa, sb, base_goals)

        is_inaugural = (mid == inaugural_id)
        tag = global_tag(pa, pd, pb, is_inaugural)

        # Context fields
        ctx = ctx_lookup.get(mid, {})
        team_a_ctx_text = ""
        team_b_ctx_text = ""
        explanation     = ""
        if ctx:
            team_a_ctx_text = ctx.get("team_a_context", {}).get("incentivo_competitivo", "") or ""
            team_b_ctx_text = ctx.get("team_b_context", {}).get("incentivo_competitivo", "") or ""
            explanation     = ctx.get("prediccion_narrativa", "") or ""

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
    lines.append("   is_premium, published, created_at, updated_at)")
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
