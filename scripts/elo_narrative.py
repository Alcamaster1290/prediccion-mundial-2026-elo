# -*- coding: utf-8 -*-
"""Narrativa v2 de predicciones.

Convierte brechas ELO en frases completas con interpretación y suma la capa
de banquillo (suplentes con buen roce de club que pueden alterar el partido).

Guía de estilo del proyecto. Todo texto generado usa frases completas y no
contiene dos puntos, punto y coma, rayas ni guiones de puntuación. Los
guiones dentro de nombres propios (Al-Sadd, Hyun-jun) sí están permitidos.
La elección de variantes léxicas es determinística por match_id (crc32),
así el mismo input produce siempre el mismo texto.
"""
import zlib

from xi_matchups import normalize_line, strongest_edge, weakest_edge

LINE_PHRASE = {
    'gk': 'el arquero',
    'defense': 'la defensa',
    'midfield': 'el mediocampo',
    'attack': 'el ataque',
}

EDGE_PHRASE = {
    'attack_vs_defense': ('el ataque', 'la defensa'),
    'midfield_vs_midfield': ('el mediocampo', 'el mediocampo'),
    'defense_vs_attack': ('la defensa', 'el ataque'),
    'gk_vs_attack': ('el arquero', 'el ataque'),
}

SUPERSUB_MIN_DELTA = 40.0


def expected_duel_pct(gap, elo_scale=400):
    """Curva ELO del modelo. Traduce una brecha de puntos al porcentaje
    esperado de duelos directos ganados por el lado favorecido."""
    return 100.0 / (1.0 + 10.0 ** (-float(gap) / float(elo_scale)))


def gap_phrase(abs_gap):
    if abs_gap < 25:
        return 'un cruce prácticamente parejo en roce de club'
    if abs_gap < 60:
        return 'una ventaja ligera'
    if abs_gap < 120:
        return 'una ventaja clara'
    if abs_gap < 200:
        return 'un dominio esperado sobre el papel'
    return 'una diferencia de categoría'


def pick(match_id, salt, options):
    """Variante determinística y reproducible (sin RNG)."""
    index = zlib.crc32(f'{match_id}|{salt}'.encode('utf-8')) % len(options)
    return options[index]


# ── Capa de banquillo ─────────────────────────────────────────────────────────

def build_bench_profiles(teams_data):
    """Perfil de banca por equipo a partir de teams.json.

    supersub es el suplente que más eleva el promedio de su línea si entra
    por el titular más bajo de esa línea. delta mide cuánto supera el ELO de
    su club al promedio titular de la línea."""
    profiles = {}
    for team in teams_data.get('teams', []):
        starters = {'gk': [], 'defense': [], 'midfield': [], 'attack': []}
        bench = []
        for player in team.get('players') or []:
            if player.get('elo') is None:
                continue
            line = normalize_line(player.get('pos'))
            if not line:
                continue
            if player.get('titular'):
                starters[line].append(float(player['elo']))
            else:
                bench.append({
                    'elo': float(player['elo']),
                    'name': player.get('name') or 'Suplente',
                    'club': (player.get('club') or '').strip(),
                    'line': line,
                })
        if not any(starters.values()) or not bench:
            continue

        best = None
        for player in bench:
            line_elos = starters.get(player['line'])
            if not line_elos:
                continue
            line_avg = sum(line_elos) / len(line_elos)
            delta = player['elo'] - line_avg
            if best is None or delta > best['delta']:
                candidate = dict(player)
                candidate['delta'] = delta
                candidate['line_avg'] = line_avg
                candidate['new_avg'] = (sum(line_elos) - min(line_elos) + player['elo']) / len(line_elos)
                best = candidate

        top5 = sorted((p['elo'] for p in bench), reverse=True)[:5]
        profiles[team['id']] = {
            'team_code': team['id'],
            'name': team.get('name') or team['id'].upper(),
            'supersub': best,
            'bench_size': len(bench),
            'bench_top5_avg': sum(top5) / len(top5) if top5 else None,
        }
    return profiles


def bench_sentence(match_id, team_name, bench_profile):
    if not bench_profile or not bench_profile.get('supersub'):
        return (
            f'El banquillo de {team_name} no ofrece un salto de nivel respecto '
            'del once inicial, así que lo que arranca es la mejor versión disponible.'
        )
    sub = bench_profile['supersub']
    line = LINE_PHRASE[sub['line']]
    club_part = f', que juega en {sub["club"]},' if sub['club'] else ','
    if sub['delta'] >= SUPERSUB_MIN_DELTA:
        options = [
            (
                f'En el banquillo de {team_name} espera {sub["name"]}{club_part} '
                f'con un roce de club de {round(sub["elo"])} puntos. Su ingreso elevaría '
                f'{line} titular de un promedio de {round(sub["line_avg"])} a cerca de '
                f'{round(sub["new_avg"])} puntos, y por eso es el cambio que puede alterar el desarrollo.'
            ),
            (
                f'{team_name} guarda una carta fuerte en {sub["name"]}{club_part} '
                f'con {round(sub["elo"])} puntos de roce de club. Si entra, {line} pasaría '
                f'de un promedio de {round(sub["line_avg"])} a cerca de {round(sub["new_avg"])} puntos, '
                'un salto capaz de cambiar el guion del partido.'
            ),
        ]
        return pick(match_id, 'bench' + team_name, options)
    if sub['delta'] > 0:
        return (
            f'La banca de {team_name} sostiene el nivel del once, con {sub["name"]}{club_part} '
            'como el recambio de mayor roce de club.'
        )
    return (
        f'El banquillo de {team_name} no sube el techo del once inicial, '
        'de modo que la versión que arranca es la más fuerte que tiene.'
    )


# ── Narrativa del cruce ───────────────────────────────────────────────────────

def _names_clause(profile, line):
    names = (profile.get('names_by_line') or {}).get(line) or []
    names = [n for n in names if n][:2]
    if not names:
        return ''
    if len(names) == 1:
        return f', con {names[0]} como referencia,'
    return f', con {names[0]} y {names[1]} como protagonistas,'


def opening_sentence(match_id, name_a, name_b, gap):
    abs_gap = abs(gap)
    gap_int = round(abs_gap)
    phrase = gap_phrase(abs_gap)
    if abs_gap < 25:
        options = [
            (
                f'Apenas {gap_int} puntos de roce de club separan al once de {name_a} '
                f'del de {name_b}, un margen que la curva ELO traduce en duelos repartidos '
                'casi a partes iguales.'
            ),
            (
                f'Los onces de {name_a} y {name_b} llegan separados por solo {gap_int} puntos '
                'de roce de club, de modo que la curva ELO anticipa duelos muy repartidos.'
            ),
            (
                f'En roce de club casi no hay distancia entre {name_a} y {name_b}, '
                f'con {gap_int} puntos de diferencia y duelos que se reparten casi a partes iguales.'
            ),
        ]
        return pick(match_id, 'opening', options)

    fav, dog = (name_a, name_b) if gap >= 0 else (name_b, name_a)
    duel = round(expected_duel_pct(abs_gap))
    options = [
        (
            f'La brecha global es de {gap_int} puntos de roce de club a favor de {fav}, '
            f'lo que en la escala ELO equivale a imponerse en unos {duel} de cada 100 duelos '
            f'directos. Se trata de {phrase}.'
        ),
        (
            f'{fav} parte con {gap_int} puntos más de roce de club que {dog}, una distancia '
            f'que la curva ELO traduce en ganar cerca de {duel} de cada 100 duelos directos. Es {phrase}.'
        ),
        (
            f'El once de {fav} promedia {gap_int} puntos más que el de {dog}, y en términos ELO '
            f'eso significa imponerse en aproximadamente {duel} de cada 100 duelos. Hablamos de {phrase}.'
        ),
    ]
    return pick(match_id, 'opening', options)


def decisive_edge_sentence(match_id, name_a, name_b, comparison):
    edges = comparison['a']['line_edges']
    key = max(edges, key=lambda k: abs(edges[k]))
    value = edges[key]
    mine, theirs = EDGE_PHRASE[key]
    points = round(abs(value))
    if value >= 0:
        names = _names_clause(comparison['a']['profile'], key.split('_vs_')[0])
        return (
            f'El cruce que más desequilibra enfrenta a {mine} de {name_a}{names} '
            f'con {theirs} de {name_b}, donde la diferencia llega a {points} puntos '
            f'a favor de {name_a}.'
        )
    mirror = {
        'attack_vs_defense': 'defense',
        'midfield_vs_midfield': 'midfield',
        'defense_vs_attack': 'attack',
        'gk_vs_attack': 'attack',
    }[key]
    names = _names_clause(comparison['b']['profile'], mirror)
    return (
        f'El cruce que más desequilibra enfrenta a {mine} de {name_a} con {theirs} '
        f'de {name_b}{names} donde {name_b} manda por {points} puntos.'
    )


def matchup_narrative(match, comparison, bench_profiles):
    """Devuelve los dos primeros párrafos de la explicación, separados por
    línea en blanco. El tercero (probabilidad y calendario) lo agrega
    generate_predictions."""
    match_id = match['match_id']
    name_a = match.get('home_name') or comparison['a']['profile']['name']
    name_b = match.get('away_name') or comparison['b']['profile']['name']
    gap = comparison['a']['profile']['xi_blend'] - comparison['b']['profile']['xi_blend']

    paragraph_one = (
        opening_sentence(match_id, name_a, name_b, gap)
        + ' '
        + decisive_edge_sentence(match_id, name_a, name_b, comparison)
    )
    paragraph_two = (
        'El partido también puede decidirse desde los cambios. '
        + bench_sentence(match_id, name_a, bench_profiles.get(match['home_team']) if bench_profiles else None)
        + ' '
        + bench_sentence(match_id, name_b, bench_profiles.get(match['away_team']) if bench_profiles else None)
    )
    return paragraph_one + '\n\n' + paragraph_two


# ── Contextos por equipo ──────────────────────────────────────────────────────

def _edge_clause(key, value):
    mine, theirs = EDGE_PHRASE[key]
    points = round(abs(value))
    if value >= 0:
        return f'{mine} frente a {theirs} rival, con {points} puntos a favor'
    return f'{mine} frente a {theirs} rival, donde cede {points} puntos'


def team_context_sentences(side, bench_profile):
    profile = side['profile']
    best_key, best_value = strongest_edge(side)
    worst_key, worst_value = weakest_edge(side)
    text = (
        f'El once promedia {profile["xi_blend"]:.1f} puntos de roce de club, '
        f'con la defensa en {profile["lines"]["defense"]:.1f}, el mediocampo en '
        f'{profile["lines"]["midfield"]:.1f} y el ataque en {profile["lines"]["attack"]:.1f}. '
        f'Su mejor argumento aparece en {_edge_clause(best_key, best_value)}, mientras que '
        f'su zona de riesgo está en {_edge_clause(worst_key, worst_value)}.'
    )
    supersub = (bench_profile or {}).get('supersub')
    if supersub and supersub['delta'] > 0:
        club_part = f' de {supersub["club"]}' if supersub['club'] else ''
        text += (
            f' Desde la banca, {supersub["name"]}{club_part} puede subir el nivel '
            f'de {LINE_PHRASE[supersub["line"]]}.'
        )
    else:
        text += ' La banca no eleva el techo del once inicial.'
    return text


def partial_side_context(profile):
    return (
        f'El once promedia {profile["xi_blend"]:.1f} puntos de roce de club, '
        f'con la defensa en {profile["lines"]["defense"]:.1f}, el mediocampo en '
        f'{profile["lines"]["midfield"]:.1f} y el ataque en {profile["lines"]["attack"]:.1f}. '
        'La comparación de líneas queda limitada porque el rival no tiene un once '
        'completo con ELO de club.'
    )


def missing_side_context(team_name):
    return (
        f'{team_name} no tiene un once titular completo con ELO de club, así que el '
        'modelo conserva su base internacional y evita inventar duelos individuales.'
    )


def partial_pair_note(name_a, name_b, profile_a, profile_b):
    if not profile_a and not profile_b:
        return (
            f'La comparación de onces es parcial porque ni {name_a} ni {name_b} tienen '
            'un once titular completo con ELO de club, de modo que el pronóstico se '
            'apoya en la base internacional y el calendario.'
        )
    available = profile_a or profile_b
    missing = name_b if profile_a else name_a
    return (
        f'La comparación de onces es parcial. {available["name"]} sí promedia '
        f'{available["xi_blend"]:.1f} puntos de roce de club, con la defensa en '
        f'{available["lines"]["defense"]:.1f}, el mediocampo en {available["lines"]["midfield"]:.1f} '
        f'y el ataque en {available["lines"]["attack"]:.1f}, mientras que {missing} no tiene un '
        'once titular completo con ELO de club, por lo que ese lado se evalúa con la base '
        'internacional sin forzar duelos individuales.'
    )
