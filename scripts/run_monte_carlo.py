#!/usr/bin/env python3
"""run_monte_carlo.py -- Monte Carlo simulation of the 2026 World Cup group stage.

Usage:
  python scripts/run_monte_carlo.py --runs 1000 --seed 42 --output data/mc_results.json

Arguments:
  --runs   N   Number of simulations (default: 1000)
  --seed   N   Random seed for reproducibility (default: no seed)
  --output     Output JSON file path (default: data/mc_results.json)
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from simulate_group_stage import (
    load_matches,
    load_strengths,
    load_xi_profiles,
    simulate_all_groups,
    best_thirds,
)

REPO_ROOT = Path(__file__).parent.parent
POSSIBLE_POINTS = (0, 1, 2, 3, 4, 5, 6, 7, 9)


def rounded_pct_distribution(point_counts, runs):
    """Return one-decimal percentages that sum exactly to 100.0."""
    raw_tenths = {
        points: (point_counts.get(points, 0) * 1000) / runs
        for points in POSSIBLE_POINTS
    }
    floors = {points: int(math.floor(value)) for points, value in raw_tenths.items()}
    remaining = 1000 - sum(floors.values())
    remainders = sorted(
        POSSIBLE_POINTS,
        key=lambda points: (raw_tenths[points] - floors[points], point_counts.get(points, 0), points),
        reverse=True,
    )
    for points in remainders[:remaining]:
        floors[points] += 1
    return {str(points): floors[points] / 10 for points in POSSIBLE_POINTS}


def run_monte_carlo(runs, seed, matches, strengths, base_goals, elo_scale=400, xi_profiles=None, xi_matchup_weight=0.20,
                    draw_bias=0.0, parity_scale=600.0, elo_lambda_scale=None):
    if seed is not None:
        random.seed(seed)

    counts = defaultdict(lambda: {
        'first': 0,
        'second': 0,
        'third': 0,
        'fourth': 0,
        'best_third': 0,
        'points': defaultdict(int),
    })

    # Per-group tracking for the terceros table
    group_thirds = defaultdict(lambda: {
        'sum_pts': 0, 'sum_gd': 0, 'sum_gf': 0, 'qualifies': 0,
        'team_counts': defaultdict(int),
    })

    for _ in range(runs):
        standings = simulate_all_groups(matches, strengths, base_goals, elo_scale, xi_profiles, xi_matchup_weight,
                                        draw_bias, parity_scale, elo_lambda_scale)

        for gid, ranked in standings.items():
            for pos, t in enumerate(ranked):
                code = t['code']
                if pos == 0:
                    counts[code]['first'] += 1
                elif pos == 1:
                    counts[code]['second'] += 1
                elif pos == 2:
                    counts[code]['third'] += 1
                    g = group_thirds[gid]
                    g['sum_pts'] += t['PTS']
                    g['sum_gd']  += t['DG']
                    g['sum_gf']  += t['GF']
                    g['team_counts'][code] += 1
                else:
                    counts[code]['fourth'] += 1
                counts[code]['points'][t['PTS']] += 1

        for i, t in enumerate(best_thirds(standings)):
            if i < 8:
                counts[t['code']]['best_third'] += 1
                group_thirds[t['group']]['qualifies'] += 1

    results = {}
    for code, c in counts.items():
        qualified = c['first'] + c['second'] + c['best_third']
        results[code] = {
            'qualified_pct':    round(100 * qualified    / runs, 1),
            'first_pct':        round(100 * c['first']   / runs, 1),
            'second_pct':       round(100 * c['second']  / runs, 1),
            'third_pct':        round(100 * c['third']   / runs, 1),
            'best_third_pct':   round(100 * c['best_third'] / runs, 1),
            'fourth_pct':       round(100 * c['fourth']  / runs, 1),
            'points_pct': rounded_pct_distribution(c['points'], runs),
        }

    # Build projected terceros table (one row per group)
    terceros_rows = []
    for gid, g in group_thirds.items():
        n = runs  # every run has exactly one third per group
        most_likely = max(g['team_counts'].items(), key=lambda x: x[1])
        terceros_rows.append({
            'group':          gid,
            'team_code':      most_likely[0],
            'third_pct':      round(100 * most_likely[1] / runs, 1),
            'qualifies_pct':  round(100 * g['qualifies'] / runs, 1),
            'avg_pts':        round(g['sum_pts'] / n, 2),
            'avg_gd':         round(g['sum_gd']  / n, 2),
            'avg_gf':         round(g['sum_gf']  / n, 2),
        })

    # Rank by FIFA criteria: pts > GD > GF
    terceros_rows.sort(key=lambda x: (-x['avg_pts'], -x['avg_gd'], -x['avg_gf']))
    for i, row in enumerate(terceros_rows):
        row['rank'] = i + 1
        row['qualifies'] = i < 8

    return results, terceros_rows


def main():
    parser = argparse.ArgumentParser(description='Monte Carlo group stage simulation')
    parser.add_argument('--runs',   type=int, default=1000)
    parser.add_argument('--seed',   type=int, default=None)
    parser.add_argument('--output', default=str(REPO_ROOT / 'data' / 'mc_results.json'))
    args = parser.parse_args()

    weights    = json.loads((REPO_ROOT / 'data' / 'model_weights.json').read_text(encoding='utf-8'))
    base_goals = weights.get('base_goals_per_team', 1.3)
    elo_scale = weights.get('elo_scale', 400)
    xi_matchup_weight = weights.get('xi_matchup_weight', 0.20)
    draw_bias = weights.get('draw_bias', 0.0)
    parity_scale = weights.get('parity_scale', 600.0)
    elo_lambda_scale = weights.get('elo_lambda_scale')

    matches   = load_matches()
    strengths = load_strengths()
    xi_profiles = load_xi_profiles()

    print(f"Running {args.runs} simulations (seed={args.seed})...")
    results_by_team, terceros_table = run_monte_carlo(
        args.runs,
        args.seed,
        matches,
        strengths,
        base_goals,
        elo_scale,
        xi_profiles,
        xi_matchup_weight,
        draw_bias,
        parity_scale,
        elo_lambda_scale,
    )

    output = {
        'runs':           args.runs,
        'seed':           args.seed,
        'version':        weights.get('_version', '1.1'),
        'xi_matchup_weight': xi_matchup_weight,
        'draw_bias':      draw_bias,
        'parity_scale':   parity_scale,
        'elo_lambda_scale': elo_lambda_scale,
        'teams':          results_by_team,
        'terceros_table': terceros_table,
    }

    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved results -> {out_path}")

    # Print top qualifiers
    sorted_teams = sorted(
        results_by_team.items(),
        key=lambda x: -x[1]['qualified_pct']
    )
    print("\nTop 10 qualification probabilities:")
    for code, r in sorted_teams[:10]:
        print(f"  {code:4s}  {r['qualified_pct']:5.1f}%  (1st:{r['first_pct']}%  2nd:{r['second_pct']}%  best3rd:{r['best_third_pct']}%)")

    print("\nTabla de mejores terceros proyectada:")
    print(f"  {'Rk':>2}  {'Grp':3}  {'Equipo':6}  {'3ro%':>5}  {'PTS':>5}  {'DG':>5}  {'GF':>5}  {'Clasif%':>7}  Q")
    for row in terceros_table:
        q = 'SI' if row['qualifies'] else '  '
        print(f"  {row['rank']:>2}  {row['group']:3}  {row['team_code']:6}  "
              f"{row['third_pct']:>5.1f}  {row['avg_pts']:>5.2f}  {row['avg_gd']:>+5.2f}  "
              f"{row['avg_gf']:>5.2f}  {row['qualifies_pct']:>7.1f}%  {q}")


if __name__ == '__main__':
    main()
