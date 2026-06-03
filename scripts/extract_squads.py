#!/usr/bin/env python3
"""extract_squads.py -- Extracts squad data from index.html team sections.

Reads the .squad-table from each analyzed team section and writes all 24 teams
into data/teams.json.  Teams already present are skipped unless --overwrite.

Run: python scripts/extract_squads.py [--overwrite]
"""
import argparse
import html as html_lib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# HTML section id -> 3-letter team code  (derived from flag img src in each section)
SECTION_MAP = {
    'alemania':       'ger',
    'austria':        'aut',
    'belgica':        'bel',
    'bosnia':         'bih',
    'brasil':         'bra',
    'cabo-verde':     'cpv',
    'colombia':       'col',
    'corea':          'kor',
    'costa-marfil':   'civ',
    'curazao':        'cuw',
    'escocia':        'sco',
    'espana':         'esp',
    'estados-unidos': 'usa',
    'francia':        'fra',
    'haiti':          'hti',
    'inglaterra':     'eng',
    'japon':          'jpn',
    'noruega':        'nor',
    'nueva-zelanda':  'nzl',
    'portugal':       'por',
    'rd-congo':       'cod',
    'suecia':         'swe',
    'suiza':          'sui',
    'tunez':          'tun',
}


def strip_tags(s):
    return html_lib.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def extract_elo(cell_text):
    """Return int ELO or None if N/D / missing."""
    t = strip_tags(cell_text)
    return int(t) if t.isdigit() else None


def parse_tbody(tbody_html):
    """Parse all <tr> rows from squad tbody.  Returns list of player dicts."""
    players = []
    for row in re.findall(r'<tr>(.*?)</tr>', tbody_html, re.DOTALL):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 7:
            continue

        pos_m = re.search(r'class="pos-badge[^"]*">([A-Z]+)<', cells[0])
        pos   = pos_m.group(1) if pos_m else ''

        name  = strip_tags(cells[1]).replace('★', '').replace('(C)', '').strip()
        age_s = strip_tags(cells[2])
        age   = int(age_s) if age_s.isdigit() else None
        club  = strip_tags(cells[3])
        country = strip_tags(cells[4])
        elo   = extract_elo(cells[5])
        titular = bool(re.search(r'titl-yes', cells[6]))

        players.append({
            'number':  None,
            'pos':     pos,
            'name':    name,
            'age':     age,
            'club':    club,
            'country': country,
            'elo':     elo,
            'titular': titular,
        })
    return players


def extract_section(full_html, section_id, code):
    """Extract one team's metadata and players from index.html."""
    marker = f'id="{section_id}"'
    idx = full_html.find(marker)
    if idx == -1:
        return None

    # Take a generous slice from the section start to find everything we need
    slice_ = full_html[idx: idx + 120_000]

    # Team name from flag img alt
    flag_re = re.search(
        r'assets/flags/' + re.escape(code) + r'\.svg[^>]*alt="([^"]+)"', slice_[:500]
    )
    name = flag_re.group(1) if flag_re else section_id

    # DT and group from team-sub
    sub_re = re.search(
        r'class="team-sub">DT:\s*([^<·]+)·\s*Grupo\s+([A-L])', slice_[:3000]
    )
    dt    = sub_re.group(1).strip() if sub_re else ''
    group = sub_re.group(2).strip() if sub_re else ''

    # Squad table tbody
    tb_start = slice_.find('<tbody>')
    tb_end   = slice_.find('</tbody>', tb_start)
    if tb_start == -1 or tb_end == -1:
        return None
    players = parse_tbody(slice_[tb_start + 7: tb_end])

    return {
        'id':       code,
        'name':     name,
        'group':    group,
        'dt':       dt,
        'analyzed': True,
        'players':  players,
    }


def main():
    parser = argparse.ArgumentParser(description='Extract squads from index.html -> teams.json')
    parser.add_argument('--overwrite', action='store_true',
                        help='Re-extract teams already present in teams.json')
    args = parser.parse_args()

    with open(REPO_ROOT / 'index.html', encoding='utf-8') as f:
        full_html = f.read()

    teams_path = REPO_ROOT / 'data' / 'teams.json'
    with open(teams_path, encoding='utf-8') as f:
        teams_data = json.load(f)

    existing = {t['id']: t for t in teams_data.get('teams', [])}
    results  = {}

    for section_id, code in SECTION_MAP.items():
        if code in existing and not args.overwrite:
            results[code] = existing[code]
            print(f'SKIP {code:4s} ({section_id}) -- already in teams.json')
            continue

        team = extract_section(full_html, section_id, code)
        if team is None:
            print(f'WARN {code:4s} ({section_id}) -- section or squad table not found')
            continue

        titulars = sum(1 for p in team['players'] if p['titular'])
        with_elo  = sum(1 for p in team['players'] if p['elo'] is not None)
        print(f'OK   {code:4s} ({section_id:16s}) '
              f'Grupo {team["group"]}  '
              f'{len(team["players"]):2d} jugadores  '
              f'{titulars} titulares  '
              f'{with_elo} con ELO')
        results[code] = team

    # Sort by group, then code
    sorted_teams = sorted(results.values(), key=lambda t: (t.get('group', 'Z'), t['id']))

    teams_data['teams'] = sorted_teams
    teams_data['meta']['total_teams_analyzed'] = len(sorted_teams)
    teams_data['meta']['updated'] = '2026-06-02'

    with open(teams_path, 'w', encoding='utf-8') as f:
        json.dump(teams_data, f, ensure_ascii=False, indent=2)

    print(f'\nActualizado teams.json: {len(sorted_teams)} equipos')


if __name__ == '__main__':
    main()
