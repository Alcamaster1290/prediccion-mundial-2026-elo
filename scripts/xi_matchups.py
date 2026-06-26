"""XI starter line matchup helpers.

Team strength already includes an aggregate XI blend. These helpers add a
match-specific layer: attack against opponent defense, midfield against
midfield, defense against opponent attack, and goalkeeper against opponent
attack. The layer is intentionally small and transparent so it explains
matchups without overwhelming the international ELO base.
"""

LINE_LABELS = {
    "gk": "arquero",
    "defense": "defensa",
    "midfield": "mediocampo",
    "attack": "ataque",
}

POSITION_LINES = {
    "GK": "gk",
    "POR": "gk",
    "DEF": "defense",
    "DF": "defense",
    "D": "defense",
    "MED": "midfield",
    "MF": "midfield",
    "MID": "midfield",
    "M": "midfield",
    "DEL": "attack",
    "FW": "attack",
    "FWD": "attack",
    "AT": "attack",
}

EDGE_WEIGHTS = {
    "attack_vs_defense": 0.35,
    "midfield_vs_midfield": 0.30,
    "defensive_unit_vs_attack": 0.35,
}

DEFENSIVE_UNIT_DEFENSE_WEIGHT = 0.25
DEFENSIVE_UNIT_GK_WEIGHT = 0.10


def average(values):
    values = [float(value) for value in values if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def normalize_line(pos):
    return POSITION_LINES.get(str(pos or "").upper())


def build_xi_profiles(teams_data):
    profiles = {}
    for team in teams_data.get("teams", []):
        by_line = {"gk": [], "defense": [], "midfield": [], "attack": []}
        names_by_line = {"gk": [], "defense": [], "midfield": [], "attack": []}
        for player in team.get("players") or []:
            if not player.get("titular") or player.get("elo") is None:
                continue
            line = normalize_line(player.get("pos"))
            if not line:
                continue
            by_line[line].append(player.get("elo"))
            names_by_line[line].append(player.get("name") or "Titular")

        xi_blend = average([elo for values in by_line.values() for elo in values])
        if xi_blend is None:
            continue

        lines = {}
        for line, values in by_line.items():
            lines[line] = average(values) if values else xi_blend

        profiles[team["id"]] = {
            "team_code": team["id"],
            "name": team.get("name") or team["id"].upper(),
            "xi_blend": xi_blend,
            "starter_count": sum(len(values) for values in by_line.values()),
            "lines": lines,
            "names_by_line": names_by_line,
        }
    return profiles


def line_edges(profile, opponent):
    defensive_unit = round(
        (
            profile["lines"]["defense"] * DEFENSIVE_UNIT_DEFENSE_WEIGHT
            + profile["lines"]["gk"] * DEFENSIVE_UNIT_GK_WEIGHT
        )
        / (DEFENSIVE_UNIT_DEFENSE_WEIGHT + DEFENSIVE_UNIT_GK_WEIGHT),
        1,
    )
    return {
        "attack_vs_defense": round(profile["lines"]["attack"] - opponent["lines"]["defense"], 1),
        "midfield_vs_midfield": round(profile["lines"]["midfield"] - opponent["lines"]["midfield"], 1),
        "defensive_unit_vs_attack": round(defensive_unit - opponent["lines"]["attack"], 1),
    }


def weighted_edge(edges):
    return round(sum(edges[key] * EDGE_WEIGHTS[key] for key in EDGE_WEIGHTS), 1)


def matchup_comparison(team_a, team_b, profiles):
    profile_a = profiles.get(team_a)
    profile_b = profiles.get(team_b)
    if not profile_a or not profile_b:
        return None

    edges_a = line_edges(profile_a, profile_b)
    edges_b = line_edges(profile_b, profile_a)
    return {
        "a": {
            "team_code": team_a,
            "profile": profile_a,
            "line_edges": edges_a,
            "weighted_edge": weighted_edge(edges_a),
        },
        "b": {
            "team_code": team_b,
            "profile": profile_b,
            "line_edges": edges_b,
            "weighted_edge": weighted_edge(edges_b),
        },
    }


def matchup_adjusted_strengths(
    team_a,
    team_b,
    strength_a,
    strength_b,
    profiles,
    xi_matchup_weight=0.20,
):
    comparison = matchup_comparison(team_a, team_b, profiles or {})
    if not comparison:
        return strength_a, strength_b, None

    effective_a = round(float(strength_a) + comparison["a"]["weighted_edge"] * xi_matchup_weight, 1)
    effective_b = round(float(strength_b) + comparison["b"]["weighted_edge"] * xi_matchup_weight, 1)
    comparison["a"]["effective_strength"] = effective_a
    comparison["b"]["effective_strength"] = effective_b
    return effective_a, effective_b, comparison


def strongest_edge(comparison_side):
    edges = comparison_side.get("line_edges") or {}
    if not edges:
        return None, 0
    key, value = max(edges.items(), key=lambda item: item[1])
    return key, value


def weakest_edge(comparison_side):
    edges = comparison_side.get("line_edges") or {}
    if not edges:
        return None, 0
    key, value = min(edges.items(), key=lambda item: item[1])
    return key, value


def edge_label(edge_key):
    return {
        "attack_vs_defense": "ataque vs defensa rival",
        "midfield_vs_midfield": "mediocampo vs mediocampo rival",
        "defensive_unit_vs_attack": "unidad defensiva vs ataque rival",
    }.get(edge_key, edge_key)


def team_xi_context(comparison_side):
    profile = comparison_side["profile"]
    best_key, best_value = strongest_edge(comparison_side)
    worst_key, worst_value = weakest_edge(comparison_side)
    return (
        f"XI blend {profile['xi_blend']:.1f}; "
        f"defensa {profile['lines']['defense']:.1f}, "
        f"medio {profile['lines']['midfield']:.1f}, "
        f"ataque {profile['lines']['attack']:.1f}. "
        f"Mayor ventaja: {edge_label(best_key)} ({best_value:+.1f}); "
        f"zona de riesgo: {edge_label(worst_key)} ({worst_value:+.1f})."
    )


def profile_xi_context(profile):
    return (
        f"XI blend {profile['xi_blend']:.1f}; "
        f"defensa {profile['lines']['defense']:.1f}, "
        f"medio {profile['lines']['midfield']:.1f}, "
        f"ataque {profile['lines']['attack']:.1f}. "
        "Comparación de líneas limitada porque el rival no tiene XI titular completo con ELO."
    )


def missing_xi_context(team_name):
    return (
        f"{team_name} no tiene XI titular completo con ELO de club; "
        "el modelo conserva la base ELO internacional para ese lado y no inventa duelos individuales."
    )


def partial_xi_matchup_note(match, team_a, team_b, profiles):
    profile_a = profiles.get(team_a)
    profile_b = profiles.get(team_b)
    if profile_a and profile_b:
        return ""
    if not profile_a and not profile_b:
        name_a = match.get("home_name") or team_a.upper()
        name_b = match.get("away_name") or team_b.upper()
        return (
            f"Comparación XI parcial: {name_a} y {name_b} no tienen XI titular completo "
            "con ELO de club; el pronóstico se apoya en ELO internacional y calendario."
        )

    available = profile_a or profile_b
    missing_name = match.get("away_name") if profile_a else match.get("home_name")
    if not missing_name:
        missing_name = (team_b if profile_a else team_a).upper()
    return (
        f"Comparación XI parcial: {available['name']} sí tiene XI blend "
        f"{available['xi_blend']:.1f} con defensa {available['lines']['defense']:.1f}, "
        f"medio {available['lines']['midfield']:.1f} y ataque {available['lines']['attack']:.1f}; "
        f"{missing_name} no tiene XI titular completo con ELO de club, por lo que no se fuerza "
        "una comparación de titulares ni una narrativa individual."
    )


def xi_matchup_note(match, comparison):
    if not comparison:
        return ""
    name_a = match.get("home_name") or comparison["a"]["profile"]["name"]
    name_b = match.get("away_name") or comparison["b"]["profile"]["name"]
    profile_a = comparison["a"]["profile"]
    profile_b = comparison["b"]["profile"]
    a_best_key, a_best_value = strongest_edge(comparison["a"])
    b_best_key, b_best_value = strongest_edge(comparison["b"])
    a_worst_key, a_worst_value = weakest_edge(comparison["a"])
    b_worst_key, b_worst_value = weakest_edge(comparison["b"])

    return (
        f"Comparación XI: {name_a} promedia {profile_a['xi_blend']:.1f} de ELO titular "
        f"y {name_b} {profile_b['xi_blend']:.1f}. "
        f"{name_a} tiene su mejor cruce en {edge_label(a_best_key)} ({a_best_value:+.1f}) "
        f"y su mayor alerta en {edge_label(a_worst_key)} ({a_worst_value:+.1f}). "
        f"{name_b} responde con {edge_label(b_best_key)} ({b_best_value:+.1f}) "
        f"y queda más expuesto en {edge_label(b_worst_key)} ({b_worst_value:+.1f})."
    )
