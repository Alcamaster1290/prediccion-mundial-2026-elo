#!/usr/bin/env python3
"""export_to_supabase.py -- Exports generated tournament data to Supabase.

Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.
Tables written: team_strength_snapshots, simulation_runs,
simulation_group_standings, simulation_terceros_table, match_results,
players, predictions, national_elo_ratings.

Usage:
  SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=... python scripts/export_to_supabase.py
  python scripts/export_to_supabase.py --strengths-only
  python scripts/export_to_supabase.py --mc-results data/mc_results.json
  python scripts/export_to_supabase.py --matches --players --predictions --national-elo
  python scripts/export_to_supabase.py --all --dry-run
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

NAMES = {
    'mex': 'Mexico', 'zaf': 'South Africa', 'kor': 'South Korea', 'cze': 'Czechia',
    'can': 'Canada', 'bih': 'Bosnia', 'qat': 'Qatar', 'sui': 'Switzerland',
    'bra': 'Brazil', 'mar': 'Morocco', 'hti': 'Haiti', 'sco': 'Scotland',
    'ger': 'Germany', 'cuw': 'Curacao', 'civ': 'Ivory Coast', 'ecu': 'Ecuador',
    'ned': 'Netherlands', 'jpn': 'Japan', 'swe': 'Sweden', 'tun': 'Tunisia',
    'bel': 'Belgium', 'egy': 'Egypt', 'irn': 'Iran', 'nzl': 'New Zealand',
    'esp': 'Spain', 'cpv': 'Cape Verde', 'ksa': 'Saudi Arabia', 'ury': 'Uruguay',
    'fra': 'France', 'sen': 'Senegal', 'irq': 'Iraq', 'nor': 'Norway',
    'arg': 'Argentina', 'alg': 'Algeria', 'aut': 'Austria', 'jor': 'Jordan',
    'por': 'Portugal', 'cod': 'DR Congo', 'uzb': 'Uzbekistan', 'col': 'Colombia',
    'eng': 'England', 'cro': 'Croatia', 'gha': 'Ghana', 'pan': 'Panama',
    'usa': 'United States', 'pry': 'Paraguay', 'aus': 'Australia', 'tur': 'Turkey',
}


def supabase_request(url, key, method, path, body=None,
                     prefer='resolution=merge-duplicates,return=minimal'):
    """Minimal Supabase REST client using stdlib (no external deps)."""
    full_url = url.rstrip('/') + '/rest/v1/' + path.lstrip('/')
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(
        full_url,
        data=data,
        method=method,
        headers={
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Prefer': prefer,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return None, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.read().decode('utf-8'), None


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def split_venue(venue):
    if not venue:
        return None, None
    parts = [p.strip() for p in str(venue).split(',')]
    stadium = parts[0] if parts else None
    city = ', '.join(parts[1:]) if len(parts) > 1 else None
    return stadium, city


def build_match_rows(groups_data, knockout_data):
    rows = []
    fixtures = []
    for group in groups_data.get('groups', []):
        group_id = group['id'].upper()
        for fixture in group.get('fixtures', []):
            item = dict(fixture)
            item['group_id'] = group_id
            fixtures.append(item)

    fixtures.sort(key=lambda f: (f.get('date') or '', f.get('time') or ''))
    for index, fixture in enumerate(fixtures, start=1):
        stadium, city = split_venue(fixture.get('venue'))
        rows.append({
            'match_number': index,
            'phase': 'group',
            'group_id': fixture['group_id'],
            'home_team': fixture.get('home'),
            'away_team': fixture.get('away'),
            'home_goals': None,
            'away_goals': None,
            'home_label': NAMES.get(fixture.get('home'), fixture.get('home')),
            'away_label': NAMES.get(fixture.get('away'), fixture.get('away')),
            'kickoff_utc': f"{fixture.get('date')}T{fixture.get('time')}:00Z",
            'stadium': stadium,
            'city': city,
            'status': 'scheduled',
        })

    for match in knockout_data:
        stadium, city_from_venue = split_venue(match.get('venue'))
        rows.append({
            'match_number': match.get('matchNum'),
            'phase': str(match.get('phase') or '').lower(),
            'group_id': None,
            'home_team': None,
            'away_team': None,
            'home_goals': None,
            'away_goals': None,
            'home_label': match.get('homeLabel'),
            'away_label': match.get('awayLabel'),
            'kickoff_utc': f"{match.get('date')}T{match.get('time')}:00Z",
            'stadium': stadium,
            'city': match.get('city') or city_from_venue,
            'status': 'scheduled',
        })

    return sorted(rows, key=lambda row: row['match_number'])


def slot_rule_from_label(match_number, side, label):
    text = str(label or '').replace('Grupo ', '').strip()
    direct = re.match(r'^([12])\D+([A-L])$', text, re.I)
    if direct:
        return {
            'match_number': match_number,
            'side': side,
            'source_type': 'group_rank',
            'source_group': direct.group(2).upper(),
            'source_rank': int(direct.group(1)),
            'source_match_number': None,
            'label': label,
        }

    winner = re.match(r'^Ganador\s+Partido\s+(\d+)$', str(label or ''), re.I)
    if winner:
        return {
            'match_number': match_number,
            'side': side,
            'source_type': 'match_winner',
            'source_group': None,
            'source_rank': None,
            'source_match_number': int(winner.group(1)),
            'label': label,
        }

    loser = re.match(r'^Perdedor\s+Partido\s+(\d+)$', str(label or ''), re.I)
    if loser:
        return {
            'match_number': match_number,
            'side': side,
            'source_type': 'match_loser',
            'source_group': None,
            'source_rank': None,
            'source_match_number': int(loser.group(1)),
            'label': label,
        }

    return {
        'match_number': match_number,
        'side': side,
        'source_type': 'manual_label',
        'source_group': None,
        'source_rank': None,
        'source_match_number': None,
        'label': label,
    }


def build_knockout_slot_rules(knockout_data):
    rows = []
    for match in knockout_data:
        match_number = match.get('matchNum')
        rows.append(slot_rule_from_label(match_number, 'home', match.get('homeLabel')))
        rows.append(slot_rule_from_label(match_number, 'away', match.get('awayLabel')))
    return rows


def build_team_rows(groups_data):
    rows = []
    memberships = []
    group_rows = []
    for draw_order, group in enumerate(groups_data.get('groups', []), start=1):
        group_id = group['id'].upper()
        group_rows.append({
            'group_id': group_id,
            'name': f'Grupo {group_id}',
            'draw_order': draw_order,
        })
        for draw_position, code in enumerate(group.get('teams', []), start=1):
            rows.append({
                'team_code': code,
                'name': NAMES.get(code, code.upper()),
                'fifa_code': code.upper(),
                'group_id': group_id,
                'flag_url': f'assets/flags/{code}.svg',
                'profile_status': 'seeded',
            })
            memberships.append({
                'group_id': group_id,
                'team_code': code,
                'draw_position': draw_position,
            })
    return group_rows, rows, memberships


def build_player_rows(teams_data, version='1.0'):
    rows = []
    for team in teams_data.get('teams', []):
        code = team['id']
        for player in team.get('players', []):
            rows.append({
                'team_code': code,
                'shirt_number': player.get('number'),
                'pos': player.get('pos'),
                'name': player.get('name'),
                'age': player.get('age'),
                'club': player.get('club'),
                'club_country': player.get('country'),
                'elo_club': player.get('elo'),
                'elo_player': None,
                'titular': bool(player.get('titular', False)),
                'version': version,
            })
    return rows


def is_publishable_team_profile(team):
    if team.get('analyzed', False):
        return True

    players = team.get('players') or []
    starter_count = sum(1 for player in players if player.get('titular') is True)
    return (
        team.get('source_status') == 'squad_only'
        and len(players) >= 26
        and starter_count >= 11
        and bool(team.get('scheme'))
        and bool(team.get('xi_image'))
        and bool(team.get('tactics'))
    )


def build_team_profile_rows(teams_data, version='1.0'):
    public_rows = []
    premium_rows = []
    for team in teams_data.get('teams', []):
        code = team['id']
        tactics = team.get('tactics') or []
        public_rows.append({
            'team_code': code,
            'summary': (tactics[0] if tactics else None),
            'tactical_style': team.get('scheme'),
            'strengths': tactics[:3],
            'weaknesses': tactics[3:],
            'version': version,
            'published': is_publishable_team_profile(team),
        })
        premium_rows.append({
            'team_code': code,
            'key_players': [team.get('star_player')] if team.get('star_player') else [],
            'premium_notes': None,
            'version': version,
        })
    return public_rows, premium_rows


def build_national_elo_rows(elo_data):
    rating_date = elo_data.get('_rating_date')
    rows = []
    for team in elo_data.get('teams', []):
        rows.append({
            'team_code': team['code'],
            'country_name': team['name'],
            'rank': team['rank'],
            'elo': team['elo'],
            'rating_date': rating_date,
            'source': 'international-football.net',
        })
    return rows


def parse_predictions_seed(sql_text):
    columns_match = re.search(r'INSERT INTO public\.predictions\s*\((.*?)\)\s*VALUES', sql_text, re.S | re.I)
    if not columns_match:
        return []
    columns = [c.strip() for c in columns_match.group(1).replace('\n', ' ').split(',')]
    rows = []
    for line in sql_text[columns_match.end():].splitlines():
        raw_line = line.strip()
        if not raw_line.startswith('('):
            continue
        raw_line = raw_line.rstrip(',;')
        if not raw_line.endswith(')'):
            continue
        raw = raw_line[1:-1]
        values = split_sql_values(raw)
        if len(values) != len(columns):
            continue
        row = {}
        for column, value in zip(columns, values):
            if value.upper() == 'NOW()':
                continue
            row[column] = sql_value_to_json(value)
        # top_scorelines viaja como literal de texto en el SQL; PostgREST
        # necesita el array JSON real para almacenarlo como jsonb.
        if isinstance(row.get('top_scorelines'), str):
            try:
                row['top_scorelines'] = json.loads(row['top_scorelines'])
            except ValueError:
                row['top_scorelines'] = None
        rows.append(row)
    return rows


def split_sql_values(raw):
    values, current, in_quote, i = [], [], False, 0
    while i < len(raw):
        ch = raw[i]
        if ch == "'":
            current.append(ch)
            if in_quote and i + 1 < len(raw) and raw[i + 1] == "'":
                current.append("'")
                i += 2
                continue
            in_quote = not in_quote
        elif ch == ',' and not in_quote:
            values.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    if current:
        values.append(''.join(current).strip())
    return values


def sql_value_to_json(value):
    upper = value.upper()
    if upper in ('NULL', 'NOW()'):
        return None
    if upper == 'TRUE':
        return True
    if upper == 'FALSE':
        return False
    if value.startswith("E'") and value.endswith("'"):
        # Cadena con escapes de Postgres (textos multipárrafo del seed).
        inner = value[2:-1].replace("''", "'")
        return inner.replace('\\n', '\n').replace('\\\\', '\\')
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def export_rows(supabase_url, service_key, table, rows, dry_run=False, conflict=None):
    if not rows:
        print(f"No rows for {table}.")
        return True
    print(f"Upserting {len(rows)} rows into {table}...")
    if dry_run:
        print(f"  Dry run: first row = {json.dumps(rows[0], ensure_ascii=True)}")
        return True
    path = table if not conflict else f'{table}?on_conflict={conflict}'
    err, _ = supabase_request(supabase_url, service_key, 'POST', path, rows)
    if err:
        print(f"ERROR exporting {table}: {err}")
        return False
    print("  Done.")
    return True


def export_tournament_core(supabase_url, service_key, groups_data, knockout_data, dry_run=False):
    group_rows, team_rows, membership_rows = build_team_rows(groups_data)
    match_rows = build_match_rows(groups_data, knockout_data)
    knockout_slot_rows = build_knockout_slot_rules(knockout_data)
    return (
        export_rows(supabase_url, service_key, 'groups', group_rows, dry_run, conflict='group_id')
        and export_rows(supabase_url, service_key, 'teams', team_rows, dry_run, conflict='team_code')
        and export_rows(supabase_url, service_key, 'group_memberships', membership_rows, dry_run, conflict='group_id,team_code')
        and export_rows(supabase_url, service_key, 'match_results', match_rows, dry_run, conflict='match_number')
        and export_rows(supabase_url, service_key, 'knockout_slot_rules', knockout_slot_rows, dry_run, conflict='match_number,side')
    )


def export_players(supabase_url, service_key, teams_data, dry_run=False):
    return export_rows(supabase_url, service_key, 'players', build_player_rows(teams_data), dry_run, conflict='team_code,name,club,version')


def export_team_profiles(supabase_url, service_key, teams_data, dry_run=False):
    public_rows, premium_rows = build_team_profile_rows(teams_data)
    return (
        export_rows(supabase_url, service_key, 'team_profiles', public_rows, dry_run, conflict='team_code')
        and export_rows(supabase_url, service_key, 'team_profile_premium', premium_rows, dry_run, conflict='team_code')
    )


def export_national_elo(supabase_url, service_key, elo_data, dry_run=False):
    return export_rows(supabase_url, service_key, 'national_elo_ratings', build_national_elo_rows(elo_data), dry_run, conflict='team_code,rating_date')


def export_predictions_seed(supabase_url, service_key, seed_sql, dry_run=False):
    rows = parse_predictions_seed(seed_sql)
    return export_rows(supabase_url, service_key, 'predictions', rows, dry_run, conflict='match_id')


def export_strengths(supabase_url, service_key, strengths_data, dry_run=False):
    version = strengths_data.get('_version', '1.0')
    rows = []
    for code, t in strengths_data['teams'].items():
        rows.append({
            'team_code':      code,
            'version':        version,
            'elo_intl':       t['elo_intl'],
            'elo_club_avg':   t.get('xi_blend'),
            'strength_score': t['strength_score'],
            'method':         t['method'],
        })

    print(f"Upserting {len(rows)} team_strength_snapshots (version={version})...")
    if dry_run:
        print(f"  Dry run: first row = {json.dumps(rows[0], ensure_ascii=True)}")
        return True
    err, _ = supabase_request(
        supabase_url, service_key, 'POST',
        'team_strength_snapshots?on_conflict=team_code,version',
        rows,
    )
    if err:
        print(f"ERROR: {err}")
        return False
    print("  Done.")
    return True


def export_mc_results(supabase_url, service_key, mc_data, version='1.0', dry_run=False):
    runs = mc_data['runs']
    seed = mc_data.get('seed')
    scenario_name = mc_data.get('scenario_name', 'baseline')
    input_hash = hashlib.sha256(
        json.dumps(mc_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()

    if dry_run:
        print(f"Dry run: would deactivate active simulation_runs for scenario={scenario_name}.")
        print(f"Dry run: would insert simulation_run runs={runs}, seed={seed}, version={version}, input_hash={input_hash[:12]}...")
        print(f"Dry run: would insert {len(mc_data['teams'])} simulation_group_standings rows.")
        print(f"Dry run: would insert {len(mc_data.get('terceros_table', []))} simulation_terceros_table rows.")
        return True

    err, _ = supabase_request(
        supabase_url, service_key, 'PATCH',
        f'simulation_runs?scenario_name=eq.{scenario_name}&is_active=eq.true',
        {'is_active': False},
        prefer='return=minimal',
    )
    if err:
        print(f"ERROR deactivating active simulation_runs: {err}")
        return False

    # Insert simulation run — must use return=representation to get the id back
    err, run_resp = supabase_request(
        supabase_url, service_key, 'POST',
        'simulation_runs',
        {
            'runs': runs,
            'seed': seed,
            'version': version,
            'scenario_name': scenario_name,
            'model_version': version,
            'is_active': True,
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'input_hash': input_hash,
        },
        prefer='return=representation',
    )
    if err:
        print(f"ERROR inserting simulation_run: {err}")
        return False

    run_id = (run_resp or [{}])[0].get('id') if run_resp else None
    if not run_id:
        print("ERROR: simulation_runs insert did not return id.")
        print("  Ensure the table exists and Prefer: return=representation is accepted.")
        print("  Check supabase/05_prediction_engine_schema.sql has been applied.")
        return False

    # Insert per-team results
    rows = []
    for code, r in mc_data['teams'].items():
        rows.append({
            'simulation_run':  run_id,
            'team_code':       code,
            'qualified_pct':   r['qualified_pct'],
            'first_pct':       r['first_pct'],
            'second_pct':      r['second_pct'],
            'third_pct':       r['third_pct'],
            'best_third_pct':  r['best_third_pct'],
            'fourth_pct':      r['fourth_pct'],
            'points_pct':      r.get('points_pct', {}),
        })

    print(f"Inserting {len(rows)} simulation_group_standings rows...")
    err, _ = supabase_request(
        supabase_url, service_key, 'POST',
        'simulation_group_standings',
        rows,
    )
    if err:
        print(f"ERROR: {err}")
        return False

    terceros_rows = []
    for row in mc_data.get('terceros_table', []):
        terceros_rows.append({
            'simulation_run': run_id,
            'rank':           row['rank'],
            'group_id':       row.get('group_id') or row.get('group'),
            'team_code':      row['team_code'],
            'third_pct':      row['third_pct'],
            'qualifies_pct':  row['qualifies_pct'],
            'avg_pts':        row['avg_pts'],
            'avg_gd':         row['avg_gd'],
            'avg_gf':         row['avg_gf'],
            'qualifies':      bool(row.get('qualifies', False)),
        })

    print(f"Inserting {len(terceros_rows)} simulation_terceros_table rows...")
    err, _ = supabase_request(
        supabase_url, service_key, 'POST',
        'simulation_terceros_table',
        terceros_rows,
    )
    if err:
        print(f"ERROR: {err}")
        return False

    print(f"  Done. Run id: {run_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Export generated tournament data to Supabase')
    parser.add_argument('--strengths-only', action='store_true',
                        help='Only export team strengths (skip MC results)')
    parser.add_argument('--mc-results',
                        default=str(REPO_ROOT / 'data' / 'mc_results.json'),
                        help='Path to mc_results.json')
    parser.add_argument('--all', action='store_true',
                        help='Export tournament core, players, national ELO, predictions, strengths, and MC results')
    parser.add_argument('--matches', action='store_true',
                        help='Export groups, teams, memberships, and match_results')
    parser.add_argument('--players', action='store_true',
                        help='Export players from data/teams.json')
    parser.add_argument('--team-profiles', action='store_true',
                        help='Export team_profiles and team_profile_premium from data/teams.json')
    parser.add_argument('--predictions', action='store_true',
                        help='Export predictions parsed from data/predictions_seed.sql')
    parser.add_argument('--national-elo', action='store_true',
                        help='Export national ELO ratings from data/international_elo.json')
    parser.add_argument('--strengths', action='store_true',
                        help='Export team strengths and MC results (also implied when no selective flag is given or with --all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print planned exports without writing to Supabase')
    args = parser.parse_args()

    # La cola de strengths + MC solía correr en CUALQUIER invocación, de modo
    # que --predictions arrastraba un nuevo simulation_run. Ahora solo corre
    # cuando se pide explícitamente (--all/--strengths/--strengths-only) o
    # cuando no se pasó ningún flag selectivo (compatibilidad con el modo sin
    # argumentos, que históricamente sincronizaba todo).
    selective_flags = (
        args.matches or args.players or args.team_profiles
        or args.predictions or args.national_elo
    )
    run_strengths_tail = (
        args.all or args.strengths or args.strengths_only or not selective_flags
    )

    supabase_url = os.environ.get('SUPABASE_URL')
    service_key  = os.environ.get('SUPABASE_SERVICE_KEY')

    if not supabase_url or not service_key:
        if args.dry_run:
            supabase_url = supabase_url or 'https://dry-run.supabase.co'
            service_key = service_key or 'dry-run-service-role'
        else:
            print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables, or use --dry-run.")
            sys.exit(1)

    if args.all or args.matches:
        groups_data = load_json(REPO_ROOT / 'data' / 'groups.json')
        knockout_data = load_json(REPO_ROOT / 'data' / 'knockout_matches.json')
        if not export_tournament_core(supabase_url, service_key, groups_data, knockout_data, dry_run=args.dry_run):
            sys.exit(1)

    if args.all or args.players or args.team_profiles:
        teams_data = load_json(REPO_ROOT / 'data' / 'teams.json')

    if args.all or args.team_profiles:
        if not export_team_profiles(supabase_url, service_key, teams_data, dry_run=args.dry_run):
            sys.exit(1)

    if args.all or args.players:
        if not export_players(supabase_url, service_key, teams_data, dry_run=args.dry_run):
            sys.exit(1)

    if args.all or args.national_elo:
        elo_data = load_json(REPO_ROOT / 'data' / 'international_elo.json')
        if not export_national_elo(supabase_url, service_key, elo_data, dry_run=args.dry_run):
            sys.exit(1)

    if args.all or args.predictions:
        seed_path = REPO_ROOT / 'data' / 'predictions_seed.sql'
        if not seed_path.exists():
            print(f"Run generate_predictions.py first: {seed_path} not found.")
            sys.exit(1)
        if not export_predictions_seed(supabase_url, service_key, seed_path.read_text(encoding='utf-8'), dry_run=args.dry_run):
            sys.exit(1)

    if not run_strengths_tail:
        return

    strengths_path = REPO_ROOT / 'data' / 'team_strength_snapshots.json'
    if not strengths_path.exists():
        print(f"Run build_team_strength.py first: {strengths_path} not found.")
        sys.exit(1)

    strengths_data = load_json(strengths_path)
    if not export_strengths(supabase_url, service_key, strengths_data, dry_run=args.dry_run):
        sys.exit(1)

    if args.strengths_only:
        return

    mc_path = Path(args.mc_results)
    if not mc_path.exists():
        print(f"Run run_monte_carlo.py first: {mc_path} not found.")
        sys.exit(1)

    mc_data = load_json(mc_path)
    strengths_version = strengths_data.get('_version', '1.0')
    version = mc_data.get('version') or strengths_version
    if mc_data.get('version') and mc_data.get('version') != strengths_version:
        print(
            f"WARN: mc_results version {mc_data.get('version')} differs from "
            f"team_strength_snapshots version {strengths_version}; exporting MC version."
        )
    if not export_mc_results(supabase_url, service_key, mc_data, version=version, dry_run=args.dry_run):
        sys.exit(1)


if __name__ == '__main__':
    main()
