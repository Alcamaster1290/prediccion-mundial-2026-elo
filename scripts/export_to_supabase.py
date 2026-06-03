#!/usr/bin/env python3
"""export_to_supabase.py -- Exports Monte Carlo results and team strengths to Supabase.

Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.
Tables written: team_strength_snapshots, simulation_runs, simulation_group_standings.

Usage:
  SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=... python scripts/export_to_supabase.py
  python scripts/export_to_supabase.py --strengths-only
  python scripts/export_to_supabase.py --mc-results data/mc_results.json --runs 1000
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def supabase_request(url, key, method, path, body=None):
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
            'Prefer': 'resolution=merge-duplicates,return=minimal',
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


def export_strengths(supabase_url, service_key, strengths_data):
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
    err, _ = supabase_request(
        supabase_url, service_key, 'POST',
        'team_strength_snapshots',
        rows,
    )
    if err:
        print(f"ERROR: {err}")
        return False
    print("  Done.")
    return True


def export_mc_results(supabase_url, service_key, mc_data):
    runs = mc_data['runs']
    seed = mc_data.get('seed')

    # Insert simulation run
    err, run_resp = supabase_request(
        supabase_url, service_key, 'POST',
        'simulation_runs?select=id',
        {'runs': runs, 'seed': seed},
    )
    if err:
        print(f"ERROR inserting simulation_run: {err}")
        return False

    run_id = (run_resp or [{}])[0].get('id') if run_resp else None
    if not run_id:
        print("Could not retrieve simulation run id — check Supabase 'Prefer: return=representation' header.")
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
    print(f"  Done. Run id: {run_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Export prediction engine data to Supabase')
    parser.add_argument('--strengths-only', action='store_true',
                        help='Only export team strengths (skip MC results)')
    parser.add_argument('--mc-results',
                        default=str(REPO_ROOT / 'data' / 'mc_results.json'),
                        help='Path to mc_results.json')
    args = parser.parse_args()

    supabase_url = os.environ.get('SUPABASE_URL')
    service_key  = os.environ.get('SUPABASE_SERVICE_KEY')

    if not supabase_url or not service_key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        sys.exit(1)

    strengths_path = REPO_ROOT / 'data' / 'team_strength_snapshots.json'
    if not strengths_path.exists():
        print(f"Run build_team_strength.py first: {strengths_path} not found.")
        sys.exit(1)

    strengths_data = load_json(strengths_path)
    if not export_strengths(supabase_url, service_key, strengths_data):
        sys.exit(1)

    if args.strengths_only:
        return

    mc_path = Path(args.mc_results)
    if not mc_path.exists():
        print(f"Run run_monte_carlo.py first: {mc_path} not found.")
        sys.exit(1)

    mc_data = load_json(mc_path)
    if not export_mc_results(supabase_url, service_key, mc_data):
        sys.exit(1)


if __name__ == '__main__':
    main()
