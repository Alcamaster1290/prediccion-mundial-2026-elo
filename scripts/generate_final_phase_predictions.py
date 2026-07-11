#!/usr/bin/env python3
"""Generate projected knockout predictions from completed group-stage data."""

import json
import math
import re
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "final_phase_predictions.json"

from elo_narrative import build_bench_profiles, matchup_narrative, partial_pair_note, polish  # noqa: E402
from elo_probability import top_scoreline_percentages  # noqa: E402
from generate_predictions import build_player_profiles, global_tag, match_probs, player_impact_sentence  # noqa: E402
from xi_matchups import build_xi_profiles, matchup_adjusted_strengths  # noqa: E402


GROUP_ORDER = {
    "A": ["mex", "zaf", "kor", "cze"],
    "B": ["can", "bih", "qat", "sui"],
    "C": ["bra", "mar", "hti", "sco"],
    "D": ["usa", "pry", "aus", "tur"],
    "E": ["ger", "cuw", "civ", "ecu"],
    "F": ["ned", "jpn", "swe", "tun"],
    "G": ["bel", "egy", "irn", "nzl"],
    "H": ["esp", "cpv", "ksa", "ury"],
    "I": ["fra", "sen", "irq", "nor"],
    "J": ["arg", "alg", "aut", "jor"],
    "K": ["por", "cod", "uzb", "col"],
    "L": ["eng", "cro", "gha", "pan"],
}

ROUND_TITLES = {
    "r32": "16avos de Final",
    "r16": "Octavos de Final",
    "qf": "Cuartos de Final",
    "sf": "Semifinales",
    "tp": "Tercer Puesto",
    "final": "Final",
}

CURRENT_BEST_THIRD_SLOT_GROUPS = {
    (74, "awayLabel"): "D",
    (77, "awayLabel"): "F",
    (79, "awayLabel"): "E",
    (80, "awayLabel"): "K",
    (81, "awayLabel"): "B",
    (82, "awayLabel"): "I",
    (85, "awayLabel"): "J",
    (87, "awayLabel"): "L",
}


class VariantAllocator:
    """Reparte las variantes léxicas del texto editorial lo más parejo posible
    para que ninguna cláusula se sobreutilice en la llave. Determinístico: gana
    la opción menos usada dentro de cada salt; los empates se rompen por crc32
    del match_id, así que el resultado es reproducible entre corridas."""

    def __init__(self):
        self._used = defaultdict(Counter)

    def pick_indexed(self, mid, salt, options, avoid=None):
        """Devuelve (índice, texto). `avoid` excluye un índice (para que el
        visitante no repita la plantilla que ya usó el local en el mismo cruce)."""
        if len(options) == 1:
            return 0, options[0]
        counts = self._used[salt]
        candidates = [i for i in range(len(options)) if i != avoid] or list(range(len(options)))
        order = sorted(
            candidates,
            key=lambda i: (counts[i], zlib.crc32(f"{mid}|{salt}|{i}".encode("utf-8"))),
        )
        idx = order[0]
        counts[idx] += 1
        return idx, options[idx]

    def pick(self, mid, salt, options):
        return self.pick_indexed(mid, salt, options)[1]


# Instancia de módulo; se reinicia al comienzo de cada build_final_predictions.
_ALLOC = VariantAllocator()


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def normalize_fixed_result(match_number, value, group_matches_by_number):
    match_number = int(match_number)
    if isinstance(value, (list, tuple)):
        fixture = group_matches_by_number.get(match_number)
        return {
            "phase": "group" if fixture else None,
            "home_team": fixture.get("home_team") if fixture else None,
            "away_team": fixture.get("away_team") if fixture else None,
            "home_goals": int(value[0]),
            "away_goals": int(value[1]),
        }
    if isinstance(value, dict):
        record = dict(value)
        record["home_goals"] = int(record["home_goals"])
        record["away_goals"] = int(record["away_goals"])
        for field in ("home_penalties", "away_penalties"):
            if record.get(field) is not None:
                record[field] = int(record[field])
        fixture = group_matches_by_number.get(match_number)
        if fixture and not record.get("phase"):
            record["phase"] = "group"
        if fixture and not record.get("home_team"):
            record["home_team"] = fixture.get("home_team")
        if fixture and not record.get("away_team"):
            record["away_team"] = fixture.get("away_team")
        return record
    raise ValueError(f"Unsupported fixed result for match {match_number}: {value!r}")


def load_fixed_result_records(path, group_matches):
    payload = load_json(path)
    group_matches_by_number = {int(match["match_number"]): match for match in group_matches}
    records = {}
    for match_number, value in (payload.get("results") or {}).items():
        records[int(match_number)] = normalize_fixed_result(match_number, value, group_matches_by_number)
    return records


def split_fixed_results(records):
    group_results = {}
    knockout_results = {}
    for match_number, record in records.items():
        phase = record.get("phase")
        if phase == "group" or match_number <= 72:
            group_results[str(match_number)] = [record["home_goals"], record["away_goals"]]
        else:
            knockout_results[match_number] = record
    return group_results, knockout_results


def result_winner(record, home, away):
    winner = record.get("winner_team")
    if winner:
        return winner
    home_goals = record.get("home_goals")
    away_goals = record.get("away_goals")
    if home_goals > away_goals:
        return home
    if away_goals > home_goals:
        return away
    home_penalties = record.get("home_penalties")
    away_penalties = record.get("away_penalties")
    if home_penalties is None or away_penalties is None:
        raise RuntimeError("Drawn knockout result requires penalty scores or winner_team")
    if home_penalties == away_penalties:
        raise RuntimeError("Penalty shootout cannot end tied")
    return home if home_penalties > away_penalties else away


def orient_result(record, home, away):
    oriented = dict(record)
    if record.get("home_team") == away and record.get("away_team") == home:
        oriented["home_team"] = home
        oriented["away_team"] = away
        oriented["home_goals"], oriented["away_goals"] = record["away_goals"], record["home_goals"]
        if record.get("home_penalties") is not None or record.get("away_penalties") is not None:
            oriented["home_penalties"] = record.get("away_penalties")
            oriented["away_penalties"] = record.get("home_penalties")
    else:
        oriented.setdefault("home_team", home)
        oriented.setdefault("away_team", away)
    return oriented


def apply_actual_result(prediction, result, home, away):
    result = orient_result(result, home, away)
    actual_winner = result_winner(result, home, away)
    actual_loser = away if actual_winner == home else home
    prediction.update({
        "status": "finished",
        "home_goals": result["home_goals"],
        "away_goals": result["away_goals"],
        "actual_winner": actual_winner,
        "actual_loser": actual_loser,
        "projected_winner": actual_winner,
        "projected_loser": actual_loser,
    })
    if result.get("home_penalties") is not None:
        prediction["home_penalties"] = result["home_penalties"]
    if result.get("away_penalties") is not None:
        prediction["away_penalties"] = result["away_penalties"]
    return prediction


def build_team_names(teams_data):
    return {
        team["id"]: team.get("name") or team["id"].upper()
        for team in teams_data.get("teams", [])
    }


def build_group_standings(matches, fixed_results):
    by_group = defaultdict(list)
    for match in matches:
        by_group[match["group"]].append(match)

    standings = {}
    for group, group_matches in by_group.items():
        stats = {
            code: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "DG": 0, "PTS": 0}
            for code in GROUP_ORDER[group]
        }
        for match in group_matches:
            score = fixed_results[str(match["match_number"])]
            home, away = match["home_team"], match["away_team"]
            home_goals, away_goals = int(score[0]), int(score[1])

            stats[home]["PJ"] += 1
            stats[away]["PJ"] += 1
            stats[home]["GF"] += home_goals
            stats[home]["GC"] += away_goals
            stats[away]["GF"] += away_goals
            stats[away]["GC"] += home_goals

            if home_goals > away_goals:
                stats[home]["PG"] += 1
                stats[home]["PTS"] += 3
                stats[away]["PP"] += 1
            elif home_goals == away_goals:
                stats[home]["PE"] += 1
                stats[away]["PE"] += 1
                stats[home]["PTS"] += 1
                stats[away]["PTS"] += 1
            else:
                stats[away]["PG"] += 1
                stats[away]["PTS"] += 3
                stats[home]["PP"] += 1

        for code, row in stats.items():
            row["DG"] = row["GF"] - row["GC"]

        ranked_codes = sorted(
            stats,
            key=lambda code: (
                -stats[code]["PTS"],
                -stats[code]["DG"],
                -stats[code]["GF"],
                GROUP_ORDER[group].index(code),
            ),
        )
        standings[group] = [
            {"code": code, "group": group, "rank": index + 1, **stats[code]}
            for index, code in enumerate(ranked_codes)
        ]
    return standings


def best_thirds(standings):
    thirds = [rows[2] for rows in standings.values()]
    thirds.sort(key=lambda row: (-row["PTS"], -row["DG"], -row["GF"], row["group"]))
    for index, row in enumerate(thirds, start=1):
        row["third_rank"] = index
        row["qualifies"] = index <= 8
    return thirds


def group_seed_label(row):
    if row["rank"] == 1:
        return f"primero del Grupo {row['group']}"
    if row["rank"] == 2:
        return f"segundo del Grupo {row['group']}"
    return f"mejor tercero del Grupo {row['group']}"


def parse_direct_slot(label):
    clean = str(label or "").replace("Grupo ", "").strip()
    match = re.match(r"^([12])[^A-L]+([A-L])$", clean)
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def parse_third_slot(label):
    clean = str(label or "").replace("Grupo ", "").strip()
    match = re.match(r"^3[^A-L]*([A-L](?:/[A-L])*)$", clean)
    if not match:
        return None
    return match.group(1).split("/")


def build_third_assignments(knockout_matches, thirds):
    third_by_group = {row["group"]: row for row in thirds}
    slots = []
    for match in knockout_matches:
        if match["phase"] != "r32":
            continue
        for side in ("homeLabel", "awayLabel"):
            groups = parse_third_slot(match.get(side))
            if not groups:
                continue
            fixed_group = CURRENT_BEST_THIRD_SLOT_GROUPS.get((match["matchNum"], side))
            candidates = [third_by_group[group] for group in groups if group in third_by_group]
            if fixed_group:
                candidates = [row for row in candidates if row["group"] == fixed_group]
            candidates.sort(key=lambda row: ((10000 if row["qualifies"] else 0) + 100 - row["third_rank"]), reverse=True)
            slots.append({"key": (match["matchNum"], side), "candidates": candidates})

    best = {}
    best_score = -math.inf

    def search(index, used_groups, assignment, score):
        nonlocal best, best_score
        if index == len(slots):
            if score > best_score:
                best_score = score
                best = dict(assignment)
            return

        slot = slots[index]
        for candidate in slot["candidates"]:
            if candidate["group"] in used_groups:
                continue
            used_groups.add(candidate["group"])
            assignment[slot["key"]] = candidate
            candidate_score = (10000 if candidate["qualifies"] else 0) + 100 - candidate["third_rank"]
            search(index + 1, used_groups, assignment, score + candidate_score)
            used_groups.remove(candidate["group"])
            del assignment[slot["key"]]

    search(0, set(), {}, 0)
    return best


def resolve_r32_team(label, match_number, side, standings, third_assignments):
    direct = parse_direct_slot(label)
    if direct:
        rank, group = direct
        return standings[group][rank - 1]
    if parse_third_slot(label):
        return third_assignments[(match_number, side)]
    return None


def knockout_match_ref(label, kind):
    pattern = r"^Ganador Partido (\d+)$" if kind == "winner" else r"^Perdedor Partido (\d+)$"
    match = re.match(pattern, str(label or ""), flags=re.I)
    return int(match.group(1)) if match else None


def advance_split(win_home, draw, win_away, effective_home, effective_away):
    shootout_home = 1.0 / (1.0 + 10.0 ** (-(effective_home - effective_away) / 600.0))
    home = win_home + draw * shootout_home
    away = win_away + draw * (1.0 - shootout_home)
    home = round(home, 1)
    away = round(100.0 - home, 1)
    return home, away


# Cláusulas de "camino del menos favorito": ideas tácticas distintas para no
# repetir siempre la misma frase. El asignador reparte cuál toca por cruce.
_UNDERDOG_PATHS = [
    "aunque {und} incomoda si aprovecha las transiciones rápidas y el balón parado.",
    "pero {und} tiene con qué sorprender si ahoga la salida rival y castiga al contragolpe.",
    "si bien {und} conserva opciones cuando el partido se abre y aparecen los espacios.",
    "aunque a {und} le puede bastar una noche fina de su referente para nivelar la serie.",
    "pero {und} sabe que la paciencia y un penal pueden estirar la eliminatoria.",
    "si {und} logra frenar el ritmo y llevarlo al desgaste, la moneda se equilibra.",
    "aunque {und} descuenta terreno si gana los duelos y la segunda pelota.",
    "pero {und} puede meterse en la serie si aguanta atrás y estira los minutos.",
    "aunque {und} tiene argumentos si el cruce se resuelve a pelota parada.",
    "si {und} acierta en las áreas, el favoritismo se diluye rápido.",
    "aunque una expulsión o un error puntual meterían a {und} de lleno en la pelea.",
    "pero {und} confía en su pegada para castigar la primera que tenga.",
    "si {und} sostiene el orden atrás, puede arrastrar el cruce a la prórroga.",
    "aunque {und} sueña con el golpe si le gana la batalla física en el medio.",
]


def _seed_context_options(team_code, seed_info, route_info, names):
    name = names[team_code]
    seed = seed_info.get(team_code)
    if seed:
        label = group_seed_label(seed)
        return "seed", [
            f"{name} cerró el grupo como {label} ({seed['PTS']} pts, {seed['DG']:+d} de diferencia).",
            f"{name} llega tras firmar {seed['PTS']} puntos en la fase de grupos, con {seed['GF']} goles a favor.",
            f"En la primera fase, {name} terminó {label} con diferencia {seed['DG']:+d}.",
            f"{name} viene de sellar el grupo con {seed['PTS']} unidades y {seed['GF']} goles.",
            f"{name} avanzó como {label}, sumando {seed['PTS']} puntos en la zona.",
        ]
    route = route_info.get(team_code)
    if route:
        return "route", [
            f"{name} se ganó el cruce dejando en el camino a {names[route['opponent']]}.",
            f"{name} aparece aquí tras superar a {names[route['opponent']]} en la ronda previa.",
            f"{name} llega con el envión de haber eliminado a {names[route['opponent']]}.",
            f"{name} dejó fuera a {names[route['opponent']]} para meterse en esta instancia.",
        ]
    return "plain", [
        f"{name} se abre paso por la ruta proyectada de la eliminatoria.",
        f"{name} sostiene su camino en el cuadro según el modelo.",
    ]


def match_seed_context(team_code, seed_info, route_info, names, mid, avoid=None):
    """Devuelve (texto, clave) donde clave=(rama, índice). `avoid` es la clave del
    contexto del otro equipo, para no repetir plantilla dentro del mismo cruce."""
    branch, options = _seed_context_options(team_code, seed_info, route_info, names)
    avoid_idx = avoid[1] if (avoid and avoid[0] == branch) else None
    idx, text = _ALLOC.pick_indexed(mid, branch, options, avoid=avoid_idx)
    return text, (branch, idx)


def editorial_text(match, home, away, pa, pb, adv_home, adv_away, seed_info, route_info, names):
    mid = f"ko-{match['matchNum']}-{home}-{away}"
    phase_name = ROUND_TITLES.get(match["phase"], match["phase"]).lower()
    favorite = home if adv_home >= adv_away else away
    underdog = away if favorite == home else home
    gap = abs(adv_home - adv_away)

    if gap < 12:
        reading = _ALLOC.pick(mid, "even", [
            f"El modelo ELO apenas separa a {names[home]} y {names[away]} en {phase_name}: un cruce de detalles.",
            f"El ELO no da ventaja clara a {names[home]} ni a {names[away]} en {phase_name}; se decidirá en los márgenes.",
            f"{names[home]} y {names[away]} llegan igualados a {phase_name}, un duelo que el ELO lee como moneda al aire.",
            f"Para el ELO hay paridad casi total entre {names[home]} y {names[away]} en {phase_name}; cualquier detalle rompe el equilibrio.",
            f"El ELO no encuentra favorito entre {names[home]} y {names[away]} en {phase_name}: se jugará al filo.",
        ])
    else:
        if gap < 30:
            opener = _ALLOC.pick(mid, "slight", [
                f"El modelo ELO inclina levemente la balanza hacia {names[favorite]} en {phase_name}",
                f"{names[favorite]} parte con una ventaja corta en {phase_name} según el ELO",
                f"El ELO da un plus a {names[favorite]} de cara a {phase_name}",
                f"El ELO ve a {names[favorite]} un paso por delante en {phase_name}",
                f"Para el ELO, {names[favorite]} llega con un favoritismo matizado a {phase_name}",
            ])
        elif gap < 55:
            opener = _ALLOC.pick(mid, "clear", [
                f"El modelo ELO perfila mejor a {names[favorite]} en {phase_name}",
                f"Para el ELO, {names[favorite]} llega como favorito claro a {phase_name}",
                f"El ELO coloca a {names[favorite]} por delante en {phase_name}",
                f"El modelo ELO se decanta con nitidez por {names[favorite]} en {phase_name}",
                f"{names[favorite]} tiene la vitola de favorito en {phase_name} para el ELO",
            ])
        else:
            opener = _ALLOC.pick(mid, "strong", [
                f"El modelo ELO marca una diferencia amplia a favor de {names[favorite]} en {phase_name}",
                f"Para el ELO, {names[favorite]} es netamente favorito en {phase_name}",
                f"El ELO ve a {names[favorite]} muy por encima en {phase_name}",
                f"El modelo ELO abre una brecha grande a favor de {names[favorite]} en {phase_name}",
                f"{names[favorite]} parte como amplio favorito en {phase_name} según el ELO",
            ])
        path = _ALLOC.pick(mid, "path", _UNDERDOG_PATHS).format(und=names[underdog])
        reading = f"{opener}, {path}"

    home_ctx, home_key = match_seed_context(home, seed_info, route_info, names, mid)
    away_ctx, _ = match_seed_context(away, seed_info, route_info, names, mid, avoid=home_key)
    return polish(f"{reading} {home_ctx} {away_ctx}")


def build_player_factor(home, away, player_profiles, names):
    home_profile = player_profiles.get(home)
    away_profile = player_profiles.get(away)
    if not home_profile and not away_profile:
        return ""

    def score(profile):
        if not profile or not profile.get("player"):
            return -1
        player = profile["player"]
        line_score = 1000 if player.get("line") in ("attack", "midfield") else 0
        return line_score + (player.get("elo") or 0)

    chosen_code = home if score(home_profile) >= score(away_profile) else away
    chosen = player_profiles.get(chosen_code)
    text = player_impact_sentence(names[chosen_code], chosen)
    if "arquero" in text.lower():
        return ""
    return polish(text)


def build_prediction(match, home, away, strengths, weights, xi_profiles, bench_profiles, player_profiles, names, seed_info, route_info):
    base_goals = weights["base_goals_per_team"]
    elo_scale = weights.get("elo_scale", 400)
    max_goals = weights.get("poisson_max_goals", 12)
    xi_matchup_weight = weights.get("xi_matchup_weight", 0.20)
    elo_lambda_scale = weights.get("elo_lambda_scale")
    draw_bias = weights.get("draw_bias", 0.0)
    parity_scale = weights.get("parity_scale", 600.0)

    strength_home = strengths.get(home, {}).get("strength_score", 1500.0)
    strength_away = strengths.get(away, {}).get("strength_score", 1500.0)
    effective_home, effective_away, comparison = matchup_adjusted_strengths(
        home,
        away,
        strength_home,
        strength_away,
        xi_profiles,
        xi_matchup_weight=xi_matchup_weight,
    )
    pa, pd, pb = match_probs(
        effective_home,
        effective_away,
        base_goals,
        elo_scale=elo_scale,
        max_goals=max_goals,
        elo_lambda_scale=elo_lambda_scale,
        draw_bias=draw_bias,
        parity_scale=parity_scale,
    )
    adv_home, adv_away = advance_split(pa, pd, pb, effective_home, effective_away)
    top_scorelines = top_scoreline_percentages(
        effective_home,
        effective_away,
        base_goals,
        elo_scale=elo_scale,
        max_goals=max_goals,
        elo_lambda_scale=elo_lambda_scale,
        draw_bias=draw_bias,
        parity_scale=parity_scale,
        top_n=10,
    )

    pseudo_match = {
        "match_id": f"ko-{match['matchNum']}-{home}-{away}",
        "home_team": home,
        "away_team": away,
        "home_name": names[home],
        "away_name": names[away],
    }
    if comparison:
        narrative = matchup_narrative(pseudo_match, comparison, bench_profiles)
        home_context = ""
        away_context = ""
    else:
        narrative = partial_pair_note(names[home], names[away], xi_profiles.get(home), xi_profiles.get(away))
        home_context = ""
        away_context = ""

    projected_winner = home if adv_home >= adv_away else away
    projected_loser = away if projected_winner == home else home
    return {
        "match_number": match["matchNum"],
        "phase": match["phase"],
        "round_name": ROUND_TITLES.get(match["phase"], match["phase"]),
        "date": match.get("date"),
        "time": match.get("time"),
        "venue": match.get("venue"),
        "city": match.get("city"),
        "home_team": home,
        "away_team": away,
        "home_name": names[home],
        "away_name": names[away],
        "home_label": match.get("homeLabel"),
        "away_label": match.get("awayLabel"),
        "team_a_win_probability": pa,
        "draw_probability": pd,
        "team_b_win_probability": pb,
        "advance_home_pct": adv_home,
        "advance_away_pct": adv_away,
        "projected_winner": projected_winner,
        "projected_loser": projected_loser,
        "global_tag": global_tag(pa, pd, pb, False),
        "editorial": editorial_text(match, home, away, pa, pb, adv_home, adv_away, seed_info, route_info, names),
        "player_factor": build_player_factor(home, away, player_profiles, names),
        "tactical_note": narrative.split("\n\n")[0] if narrative else "",
        "team_home_context": home_context,
        "team_away_context": away_context,
        "top_scorelines": top_scorelines,
    }


def build_final_predictions(fixed_results_path=None):
    global _ALLOC
    _ALLOC = VariantAllocator()  # reparto de variantes limpio y determinístico por corrida
    matches = load_json(DATA_DIR / "matches.json")
    fixed_results_path = Path(fixed_results_path) if fixed_results_path else DATA_DIR / "fixed_results.json"
    fixed_records = load_fixed_result_records(fixed_results_path, matches)
    group_results, knockout_results = split_fixed_results(fixed_records)
    knockout_matches = load_json(DATA_DIR / "knockout_matches.json")
    teams_data = load_json(DATA_DIR / "teams.json")
    strengths = load_json(DATA_DIR / "team_strength_snapshots.json")
    weights = load_json(DATA_DIR / "model_weights.json")

    standings = build_group_standings(matches, group_results)
    thirds = best_thirds(standings)
    third_assignments = build_third_assignments(knockout_matches, thirds)
    seed_info = {row["code"]: row for rows in standings.values() for row in rows if row["rank"] <= 2}
    seed_info.update({row["code"]: row for row in thirds[:8]})
    names = build_team_names(teams_data)
    xi_profiles = build_xi_profiles(teams_data)
    bench_profiles = build_bench_profiles(teams_data)
    player_profiles = build_player_profiles(teams_data)

    route_info = {}
    winners = {}
    losers = {}
    output_matches = []

    for match in sorted(knockout_matches, key=lambda item: item["matchNum"]):
        match_number = match["matchNum"]
        prediction_match = dict(match)
        if match["phase"] == "r32":
            home_row = resolve_r32_team(match["homeLabel"], match_number, "homeLabel", standings, third_assignments)
            away_row = resolve_r32_team(match["awayLabel"], match_number, "awayLabel", standings, third_assignments)
            home, away = home_row["code"], away_row["code"]
            for side in ("homeLabel", "awayLabel"):
                third = third_assignments.get((match_number, side))
                if third:
                    prediction_match[side] = f"Mejor 3. Grupo {third['group']}"
        else:
            home_win_ref = knockout_match_ref(match.get("homeLabel"), "winner")
            away_win_ref = knockout_match_ref(match.get("awayLabel"), "winner")
            home_loss_ref = knockout_match_ref(match.get("homeLabel"), "loser")
            away_loss_ref = knockout_match_ref(match.get("awayLabel"), "loser")
            home = winners.get(home_win_ref) if home_win_ref else losers.get(home_loss_ref)
            away = winners.get(away_win_ref) if away_win_ref else losers.get(away_loss_ref)
            if not home or not away:
                raise RuntimeError(f"Cannot resolve knockout match {match_number}")

        prediction = build_prediction(
            prediction_match,
            home,
            away,
            strengths["teams"],
            weights,
            xi_profiles,
            bench_profiles,
            player_profiles,
            names,
            seed_info,
            route_info,
        )
        actual_result = knockout_results.get(match_number)
        if actual_result:
            prediction = apply_actual_result(prediction, actual_result, home, away)
        output_matches.append(prediction)
        winners[match_number] = prediction["projected_winner"]
        losers[match_number] = prediction["projected_loser"]
        route_info[prediction["projected_winner"]] = {
            "match_number": match_number,
            "opponent": prediction["projected_loser"],
        }

    rounds = []
    for phase in ("r32", "r16", "qf", "sf", "tp", "final"):
        phase_matches = [match for match in output_matches if match["phase"] == phase]
        if phase_matches:
            rounds.append({"phase": phase, "title": ROUND_TITLES[phase], "matches": phase_matches})

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "fixed_count": len(group_results),
            "knockout_fixed_count": len(knockout_results),
            "finished_count": len(group_results) + len(knockout_results),
            "model_version": strengths.get("_version", weights.get("version", "1.3")),
            "best_third_groups": [row["group"] for row in thirds[:8]],
        },
        "rounds": rounds,
        "matches": output_matches,
    }


def main():
    data = build_final_predictions()
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(data['matches'])} knockout predictions -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
