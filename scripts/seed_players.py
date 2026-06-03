#!/usr/bin/env python3
"""seed_players.py -- Populates the Supabase 'players' table from data/teams.json.

Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.
Run: SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/seed_players.py

Upserts on (team_code, name, version). Safe to run multiple times.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def supabase_upsert(supabase_url, service_key, table, rows, conflict='team_code,name,version'):
    url = supabase_url.rstrip('/') + '/rest/v1/' + table
    data = json.dumps(rows).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, method='POST',
        headers={
            'apikey':        service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type':  'application/json',
            'Prefer':        f'resolution=merge-duplicates,return=minimal',
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return None
    except urllib.error.HTTPError as e:
        return e.read().decode('utf-8')


def main():
    supabase_url = os.environ.get('SUPABASE_URL')
    service_key  = os.environ.get('SUPABASE_SERVICE_KEY')
    if not supabase_url or not service_key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        sys.exit(1)

    with open(REPO_ROOT / 'data' / 'teams.json', encoding='utf-8') as f:
        teams_data = json.load(f)

    version = '1.0'
    rows = []
    for team in teams_data.get('teams', []):
        code = team['id']
        for p in team.get('players', []):
            rows.append({
                'team_code':    code,
                'shirt_number': p.get('number'),
                'pos':          p.get('pos'),
                'name':         p.get('name'),
                'age':          p.get('age'),
                'club':         p.get('club'),
                'elo_club':     p.get('elo'),
                'elo_player':   None,
                'titular':      bool(p.get('titular', False)),
                'version':      version,
            })

    if not rows:
        print("No player rows found in data/teams.json.")
        sys.exit(0)

    print(f"Upserting {len(rows)} players from {len(teams_data.get('teams',[]))} analyzed teams...")
    err = supabase_upsert(supabase_url, service_key, 'players', rows)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)
    print("Done.")


if __name__ == '__main__':
    main()
