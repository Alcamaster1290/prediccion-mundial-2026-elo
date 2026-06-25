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
import re
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
IMPACT_SUB_LINES = ('attack', 'midfield')


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


# ── Pulido de texto ───────────────────────────────────────────────────────────

_CONTRACTIONS = (
    (re.compile(r'\bde el\b'), 'del'),
    (re.compile(r'\ba el\b'), 'al'),
)
_REPEATED_PERIOD = re.compile(r'\.\.+')


def polish(text):
    """Corrige contracciones del español (de el → del, a el → al) y colapsa
    los puntos repetidos que aparecen cuando un nombre que ya termina en punto
    (EE.UU.) cierra una oración. Determinístico e idempotente."""
    if not text:
        return text
    for pattern, replacement in _CONTRACTIONS:
        text = pattern.sub(replacement, text)
    return _REPEATED_PERIOD.sub('.', text)


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

        candidates = []
        for player in bench:
            line_elos = starters.get(player['line'])
            if not line_elos:
                continue
            line_avg = sum(line_elos) / len(line_elos)
            delta = player['elo'] - line_avg
            candidate = dict(player)
            candidate['delta'] = delta
            candidate['line_avg'] = line_avg
            candidate['new_avg'] = (sum(line_elos) - min(line_elos) + player['elo']) / len(line_elos)
            candidates.append(candidate)

        impact_candidates = [
            player for player in candidates
            if player['line'] in IMPACT_SUB_LINES and player['delta'] > 0
        ]
        best = max(impact_candidates, key=lambda player: player['delta']) if impact_candidates else None

        top5 = sorted((p['elo'] for p in bench), reverse=True)[:5]
        profiles[team['id']] = {
            'team_code': team['id'],
            'name': team.get('name') or team['id'].upper(),
            'supersub': best,
            'bench_size': len(bench),
            'bench_top5_avg': sum(top5) / len(top5) if top5 else None,
        }
    return profiles


def bench_sentence(match_id, team_name, bench_profile, avoid_index=None):
    """Devuelve (texto, índice_de_variante). El índice solo es relevante en la
    rama de supersub con varias variantes; se usa para que el visitante no
    repita la misma plantilla que el local en un mismo partido. avoid_index
    fuerza una variante distinta cuando coincidiría con la del otro equipo."""
    if not bench_profile or not bench_profile.get('supersub'):
        return (
            f'El banquillo de {team_name} no ofrece un salto de nivel respecto '
            'del once inicial, así que lo que arranca es la mejor versión disponible.'
        ), None
    sub = bench_profile['supersub']
    line = LINE_PHRASE[sub['line']]
    club_part = f', que juega en {sub["club"]},' if sub['club'] else ','
    if sub['delta'] >= SUPERSUB_MIN_DELTA:
        options = [
            (
                f'En el banquillo de {team_name} espera {sub["name"]}{club_part} '
                f'con roce competitivo para subir el ritmo de {line}. Su ingreso puede '
                'cambiar alturas, acelerar la circulación y alterar el desarrollo.'
            ),
            (
                f'{team_name} guarda una carta fuerte en {sub["name"]}{club_part} '
                'con roce de club para sostener el impacto desde la banca. Si entra, '
                f'{line} gana energía y el guion del partido puede cambiar.'
            ),
            (
                f'El revulsivo de {team_name} es {sub["name"]}{club_part} y aporta '
                f'roce de club desde la banca. Con él en cancha, {line} puede jugar '
                'más arriba y sostener mejor los duelos.'
            ),
            (
                f'Si el plan no funciona, {team_name} tiene en {sub["name"]}{club_part} '
                f'un recambio con roce de club para refrescar {line} y cambiar la '
                'dirección emocional del partido.'
            ),
        ]
        index = zlib.crc32(f'{match_id}|bench{team_name}'.encode('utf-8')) % len(options)
        if avoid_index is not None and index == avoid_index:
            index = (index + 1) % len(options)
        return options[index], index
    if sub['delta'] > 0:
        return (
            f'La banca de {team_name} sostiene el nivel del once, con {sub["name"]}{club_part} '
            'como el recambio de mayor roce de club.'
        ), None
    return (
        f'El banquillo de {team_name} no sube el techo del once inicial, '
        'de modo que la versión que arranca es la más fuerte que tiene.'
    ), None


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
    phrase = gap_phrase(abs_gap)
    if abs_gap < 25:
        options = [
            (
                f'Los onces de {name_a} y {name_b} llegan casi en la misma línea de '
                'roce de club, un margen que la curva ELO lee como un partido de detalles.'
            ),
            (
                f'Entre {name_a} y {name_b} no aparece una distancia fuerte en roce de club, '
                'así que el modelo espera un cruce abierto y muy sensible al primer golpe.'
            ),
            (
                f'En roce de club casi no hay distancia entre {name_a} y {name_b}, '
                'con duelos que pueden girar por ritmo, precisión y lectura de los espacios.'
            ),
        ]
        return pick(match_id, 'opening', options)

    fav, dog = (name_a, name_b) if gap >= 0 else (name_b, name_a)
    options = [
        (
            f'La lectura global del roce de club favorece a {fav}. La curva ELO lo interpreta '
            f'como {phrase}, aunque {dog} conserva caminos si logra bajar el ritmo y proteger su área.'
        ),
        (
            f'{fav} parte mejor perfilado que {dog} por jerarquía de once y roce de club. '
            f'La ventaja no decide sola el partido, pero sí ordena la lectura inicial como {phrase}.'
        ),
        (
            f'El once de {fav} llega con más respaldo competitivo que el de {dog}. En términos '
            f'de modelo, eso coloca el partido en zona de {phrase}.'
        ),
    ]
    return pick(match_id, 'opening', options)


def line_activation(label):
    actions = {
        'el arquero': 'se apoya en el arquero',
        'la defensa': 'se ordena desde la defensa',
        'el mediocampo': 'activa el mediocampo',
        'el ataque': 'activa el ataque',
    }
    return actions.get(label, f'activa {label}')


def protection_clause(team_name, label):
    actions = {
        'el arquero': f'{team_name} protege su arco',
        'la defensa': f'{team_name} ordena su defensa',
        'el mediocampo': f'{team_name} sostiene su mediocampo',
        'el ataque': f'{team_name} conserva altura en ataque',
    }
    return actions.get(label, f'{team_name} protege {label}')


def target_sector(label):
    sectors = {
        'el arquero': 'la zona del arquero',
        'la defensa': 'la defensa',
        'el mediocampo': 'el mediocampo',
        'el ataque': 'el ataque',
    }
    return sectors.get(label, label)


def sentence_start(label):
    return label[:1].upper() + label[1:]


def terminal_names_clause(names):
    return names.rstrip(',')


def decisive_edge_sentence(match_id, name_a, name_b, comparison):
    edges = comparison['a']['line_edges']
    key = max(edges, key=lambda k: abs(edges[k]))
    value = edges[key]
    mine, theirs = EDGE_PHRASE[key]
    if value >= 0:
        names = _names_clause(comparison['a']['profile'], key.split('_vs_')[0])
        variant = zlib.crc32(f'{match_id}|edge-positive'.encode('utf-8')) % 4
        if variant == 1:
            return (
                f'La zona que abre el partido está en {mine} de {name_a}{names} '
                f'contra {theirs} de {name_b}. Ahí {name_a} puede romper el equilibrio.'
            )
        if variant == 2:
            return (
                f'El punto de presión aparece cuando {name_a} {line_activation(mine)}{names} '
                f'frente a {theirs} de {name_b}. Esa relación explica su mejor camino.'
            )
        if variant == 3:
            return (
                f'La lectura individual favorece a {name_a} en {mine}{names} '
                f'ante {theirs} de {name_b}. Si ese sector manda, el partido cambia de ritmo.'
            )
        return (
            f'El cruce que más desequilibra enfrenta a {mine} de {name_a}{names} '
            f'con {theirs} de {name_b}, donde {name_a} encuentra su ventaja más clara.'
        )
    mirror = {
        'attack_vs_defense': 'defense',
        'midfield_vs_midfield': 'midfield',
        'defense_vs_attack': 'attack',
        'gk_vs_attack': 'attack',
    }[key]
    names = _names_clause(comparison['b']['profile'], mirror)
    terminal_names = terminal_names_clause(names)
    threat_start = sentence_start(theirs)
    target = target_sector(mine)
    variant = zlib.crc32(f'{match_id}|edge-negative'.encode('utf-8')) % 4
    if variant == 1:
        return (
            f'La zona que puede torcer el guion queda del lado de {name_b}. '
            f'{threat_start}{names} castiga {target} de {name_a}.'
        )
    if variant == 2:
        return (
            f'El foco está en cómo {protection_clause(name_a, mine)} cuando aparece {theirs} '
            f'de {name_b}{terminal_names}. Esa es la alerta principal.'
        )
    if variant == 3:
        return (
            f'{name_b} encuentra su mejor argumento al atacar {target} de {name_a}. '
            f'{threat_start}{names} sostiene ese margen.'
        )
    return (
        f'El cruce que más desequilibra enfrenta a {mine} de {name_a} con {theirs} '
        f'de {name_b}{names} donde {name_b} encuentra su ventaja más clara.'
    )


def bench_lead_sentence(match_id):
    return pick(match_id, 'bench-lead', [
        'Desde la banca también aparece una capa de lectura.',
        'Los cambios pueden pesar si el partido se estira.',
        'El segundo tiempo también tiene nombres para mover el plan.',
        'La gestión de suplentes suma otro matiz al pronóstico.',
    ])


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
    home_bench = bench_profiles.get(match['home_team']) if bench_profiles else None
    away_bench = bench_profiles.get(match['away_team']) if bench_profiles else None
    home_text, home_index = bench_sentence(match_id, name_a, home_bench)
    away_text, _ = bench_sentence(match_id, name_b, away_bench, avoid_index=home_index)
    paragraph_two = bench_lead_sentence(match_id) + ' ' + home_text + ' ' + away_text
    return polish(paragraph_one + '\n\n' + paragraph_two)


# ── Contextos por equipo ──────────────────────────────────────────────────────

def _edge_clause(key, value):
    mine, theirs = EDGE_PHRASE[key]
    if value >= 0:
        return f'{mine} frente a {theirs} rival, donde puede imponer condiciones'
    return f'{mine} frente a {theirs} rival, donde necesita protección colectiva'


def team_context_sentences(side, bench_profile):
    profile = side['profile']
    best_key, best_value = strongest_edge(side)
    worst_key, worst_value = weakest_edge(side)
    text = (
        'El once tiene una lectura clara de defensa, mediocampo, ataque y roce de club. '
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
    return polish(text)


def partial_side_context(profile):
    return polish(
        'El once tiene una base legible de roce de club, pero la comparación de '
        'líneas queda limitada porque el rival no tiene un once '
        'completo con ELO de club.'
    )


def missing_side_context(team_name):
    return polish(
        f'{team_name} no tiene un once titular completo con ELO de club, así que el '
        'modelo conserva su base internacional y evita inventar duelos individuales.'
    )


def partial_pair_note(name_a, name_b, profile_a, profile_b):
    if not profile_a and not profile_b:
        return polish(
            f'La comparación de onces es parcial porque ni {name_a} ni {name_b} tienen '
            'un once titular completo con ELO de club, de modo que el pronóstico se '
            'apoya en la base internacional y el calendario.'
        )
    available = profile_a or profile_b
    missing = name_b if profile_a else name_a
    return polish(
        f'La comparación de onces es parcial. {available["name"]} sí tiene una base '
        f'de roce de club para leer sus líneas, mientras que {missing} no tiene un once '
        'titular completo con ELO de club. Ese lado se evalúa con la base internacional '
        'sin forzar duelos individuales.'
    )
