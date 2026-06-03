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
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from simulate_group_stage import (
    load_matches,
    load_strengths,
    simulate_all_groups,
    best_thirds,
)

REPO_ROOT = Path(__file__).parent.parent


def run_monte_carlo(runs, seed, matches, strengths, base_goals):
    if seed is not None:
        random.seed(seed)

    counts = defaultdict(lambda: {'first': 0, 'second': 0, 'third': 0, 'fourth': 0, 'best_third': 0})

    for _ in range(runs):
        standings = simulate_all_groups(matches, strengths, base_goals)

        for gid, ranked in standings.items():
            for pos, t in enumerate(ranked):
                code = t['code']
                if pos == 0:
                    counts[code]['first'] += 1
                elif pos == 1:
                    counts[code]['second'] += 1
                elif pos == 2:
                    counts[code]['third'] += 1
                else:
                    counts[code]['fourth'] += 1

        for i, t in enumerate(best_thirds(standings)):
            if i < 8:
                counts[t['code']]['best_third'] += 1

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
        }

    return results


def main():
    parser = argparse.ArgumentParser(description='Monte Carlo group stage simulation')
    parser.add_argument('--runs',   type=int, default=1000)
    parser.add_argument('--seed',   type=int, default=None)
    parser.add_argument('--output', default=str(REPO_ROOT / 'data' / 'mc_results.json'))
    args = parser.parse_args()

    weights    = json.loads((REPO_ROOT / 'data' / 'model_weights.json').read_text(encoding='utf-8'))
    base_goals = weights.get('base_goals_per_team', 1.3)

    matches   = load_matches()
    strengths = load_strengths()

    print(f"Running {args.runs} simulations (seed={args.seed})...")
    results_by_team = run_monte_carlo(args.runs, args.seed, matches, strengths, base_goals)

    output = {
        'runs': args.runs,
        'seed': args.seed,
        'teams': results_by_team,
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


if __name__ == '__main__':
    main()
