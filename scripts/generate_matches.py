#!/usr/bin/env python3
"""generate_matches.py — Reads data/groups.json and writes data/matches.json.

Run: python scripts/generate_matches.py
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GROUPS_JSON = REPO_ROOT / 'data' / 'groups.json'
MATCHES_JSON = REPO_ROOT / 'data' / 'matches.json'

TEAM_NAMES = {
    'mex': 'México',       'zaf': 'Sudáfrica',        'kor': 'Corea del Sur', 'cze': 'Chequia',
    'can': 'Canadá',       'bih': 'Bosnia',            'qat': 'Qatar',         'sui': 'Suiza',
    'bra': 'Brasil',       'mar': 'Marruecos',         'hti': 'Haití',         'sco': 'Escocia',
    'ger': 'Alemania',     'cuw': 'Curazao',           'civ': 'Costa de Marfil', 'ecu': 'Ecuador',
    'ned': 'Países Bajos', 'jpn': 'Japón',             'swe': 'Suecia',        'tun': 'Túnez',
    'bel': 'Bélgica',      'egy': 'Egipto',            'irn': 'Irán',          'nzl': 'Nueva Zelanda',
    'esp': 'España',       'cpv': 'Cabo Verde',        'ksa': 'Arabia Saudita', 'ury': 'Uruguay',
    'fra': 'Francia',      'sen': 'Senegal',           'irq': 'Irak',          'nor': 'Noruega',
    'arg': 'Argentina',    'alg': 'Argelia',           'aut': 'Austria',       'jor': 'Jordania',
    'por': 'Portugal',     'cod': 'RD Congo',          'uzb': 'Uzbekistán',    'col': 'Colombia',
    'eng': 'Inglaterra',   'cro': 'Croacia',           'gha': 'Ghana',         'pan': 'Panamá',
    'usa': 'EE.UU.',       'pry': 'Paraguay',          'aus': 'Australia',     'tur': 'Turquía',
}


def load_groups():
    with open(GROUPS_JSON, encoding='utf-8') as f:
        return json.load(f)['groups']


def make_match_id(group_id, jornada, home, away):
    return f"grp-{group_id.lower()}-j{jornada}-{home}-{away}"


def generate():
    groups = load_groups()

    all_fixtures = []
    for g in groups:
        gid = g['id'].lower()
        for f in g['fixtures']:
            all_fixtures.append({
                'group_id': gid,
                'jornada': f['jornada'],
                'date': f['date'],
                'time': f['time'],
                'home': f['home'],
                'away': f['away'],
                'venue': f.get('venue', ''),
            })

    # Sort by date+time (same order as seed_matches.js) for consistent match numbering
    all_fixtures.sort(key=lambda x: (x['date'], x['time']))

    matches = []
    for i, f in enumerate(all_fixtures):
        matches.append({
            'match_id':     make_match_id(f['group_id'], f['jornada'], f['home'], f['away']),
            'match_number': i + 1,
            'group':        f['group_id'].upper(),
            'jornada':      f['jornada'],
            'date':         f['date'],
            'time':         f['time'],
            'venue':        f['venue'],
            'home_team':    f['home'],
            'away_team':    f['away'],
            'home_name':    TEAM_NAMES.get(f['home'], f['home']),
            'away_name':    TEAM_NAMES.get(f['away'], f['away']),
        })

    with open(MATCHES_JSON, 'w', encoding='utf-8') as fh:
        json.dump(matches, fh, ensure_ascii=False, indent=2)

    print(f"Generated {len(matches)} matches -> {MATCHES_JSON}")
    return matches


if __name__ == '__main__':
    generate()
