#!/usr/bin/env python3
"""calibration_report.py -- Calibration diagnostics for the group-stage engine.

Measures how "football-realistic" the simulation engine is before/after tuning:
draw rate, goals per match, common scorelines, blowouts and the global
distribution of final group-stage points (0,1,2,3,4,5,6,7,9).

Match-level metrics are computed exactly from the same adjusted Poisson score
matrix the simulator samples from (no MC noise). The points distributions are
estimated with Monte Carlo using the exact same `simulate_match` engine.

Usage:
  python scripts/calibration_report.py --runs 10000 --seed 42
  python scripts/calibration_report.py --runs 1000 --seed 42 --output data/calibration_report.json
  python scripts/calibration_report.py --grid --grid-runs 1000 --seed 42

Calibration targets (group stage, World Cup-like football):
  draw_rate            24% - 31%
  goals_per_match      2.3 - 2.8
  zero_zero_rate        5% - 10%
  one_one_rate          8% - 14%
  blowout_3plus_rate   <= 18%
  points_distribution  visible mass on 1, 2, 4, 5 and 7 points

Do not commit generated report files: they are derived from the premium model.
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from simulate_group_stage import (
    load_matches,
    load_strengths,
    load_xi_profiles,
    match_score_sampler,
    simulate_match,
)
from xi_matchups import matchup_adjusted_strengths
from elo_probability import match_lambdas

REPO_ROOT = Path(__file__).parent.parent
POSSIBLE_POINTS = (0, 1, 2, 3, 4, 5, 6, 7, 9)
INTERMEDIATE_POINTS = (1, 2, 4, 5, 7)

TARGETS = {
    'draw_rate':          (0.24, 0.31),
    'goals_per_match':    (2.30, 2.80),
    'zero_zero_rate':     (0.05, 0.10),
    'one_one_rate':       (0.08, 0.14),
    'blowout_3plus_rate': (0.00, 0.18),
}

# Grid-search candidates (Task 3)
GRID_BASE_GOALS = (1.10, 1.15, 1.20, 1.25, 1.30)
GRID_LAMBDA_SCALE = (400, 500, 600)   # legacy divisor equivalent: 800, 1000, 1200
GRID_DRAW_BIAS = (0.00, 0.04, 0.06, 0.08, 0.10)


def load_weights():
    return json.loads((REPO_ROOT / 'data' / 'model_weights.json').read_text(encoding='utf-8'))


def build_match_table(matches, strengths, xi_profiles, xi_matchup_weight):
    """Effective (XI-adjusted) strengths per fixture. Deterministic."""
    table = []
    for m in matches:
        h, a = m['home_team'], m['away_team']
        sh = strengths.get(h, 1600)
        sa = strengths.get(a, 1600)
        eff_h, eff_a, _ = matchup_adjusted_strengths(
            h, a, sh, sa, xi_profiles, xi_matchup_weight=xi_matchup_weight)
        table.append({
            'match_id': m['match_id'],
            'group': m['group'],
            'home': h,
            'away': a,
            'eff_home': eff_h,
            'eff_away': eff_a,
        })
    return table


def analytic_match_metrics(entry, params):
    """Exact metrics from the adjusted score matrix used by the simulator."""
    la, lb = match_lambdas(entry['eff_home'], entry['eff_away'],
                           params['base_goals_per_team'], params['elo_scale'],
                           params['elo_lambda_scale'])
    scores, cumulative = match_score_sampler(
        round(la, 6), round(lb, 6),
        round(entry['eff_home'] - entry['eff_away'], 1),
        params['draw_bias'], params['parity_scale'])
    total = cumulative[-1]

    p_home = p_draw = p_away = 0.0
    exp_goals = p00 = p11 = p22 = blowout = 0.0
    prev = 0.0
    score_probs = {}
    for (ga, gb), cum in zip(scores, cumulative):
        p = (cum - prev) / total
        prev = cum
        score_probs[(ga, gb)] = p
        exp_goals += p * (ga + gb)
        if ga > gb:
            p_home += p
        elif ga == gb:
            p_draw += p
        else:
            p_away += p
        if (ga, gb) == (0, 0):
            p00 = p
        elif (ga, gb) == (1, 1):
            p11 = p
        elif (ga, gb) == (2, 2):
            p22 = p
        if abs(ga - gb) >= 3:
            blowout += p

    return {
        'p_home': p_home,
        'p_draw': p_draw,
        'p_away': p_away,
        'expected_goals': exp_goals,
        'p_0_0': p00,
        'p_1_1': p11,
        'p_2_2': p22,
        'p_blowout_3plus': blowout,
        'p_favorite': max(p_home, p_away),
        'score_probs': score_probs,
    }


def analytic_report(match_table, params):
    """Average exact match metrics over the 72 fixtures."""
    per_match = []
    agg = defaultdict(float)
    scoreline_probs = Counter()
    for entry in match_table:
        metrics = analytic_match_metrics(entry, params)
        per_match.append((entry, metrics))
        for key in ('p_home', 'p_draw', 'p_away', 'expected_goals',
                    'p_0_0', 'p_1_1', 'p_2_2', 'p_blowout_3plus', 'p_favorite'):
            agg[key] += metrics[key]
        for score, p in metrics['score_probs'].items():
            scoreline_probs[score] += p

    n = len(per_match)
    summary = {
        'draw_rate':          round(agg['p_draw'] / n, 4),
        'home_win_rate':      round(agg['p_home'] / n, 4),
        'away_win_rate':      round(agg['p_away'] / n, 4),
        'goals_per_match':    round(agg['expected_goals'] / n, 3),
        'goals_per_team':     round(agg['expected_goals'] / (2 * n), 3),
        'zero_zero_rate':     round(agg['p_0_0'] / n, 4),
        'one_one_rate':       round(agg['p_1_1'] / n, 4),
        'two_two_rate':       round(agg['p_2_2'] / n, 4),
        'blowout_3plus_rate': round(agg['p_blowout_3plus'] / n, 4),
        'favorite_win_rate':  round(agg['p_favorite'] / n, 4),
        'most_common_scorelines': [
            {'score': f'{ga}-{gb}', 'pct': round(100 * p / n, 2)}
            for (ga, gb), p in scoreline_probs.most_common(10)
        ],
    }
    return summary, per_match


def top_matches(per_match, key, reverse=True, limit=10):
    ranked = sorted(per_match, key=lambda item: item[1][key], reverse=reverse)
    rows = []
    for entry, metrics in ranked[:limit]:
        rows.append({
            'match_id': entry['match_id'],
            'group': entry['group'],
            'home': entry['home'],
            'away': entry['away'],
            'p_home': round(metrics['p_home'], 3),
            'p_draw': round(metrics['p_draw'], 3),
            'p_away': round(metrics['p_away'], 3),
        })
    return rows


def monte_carlo_report(match_table, params, runs, seed):
    """Simulated match stats + points distributions, same engine as MC runner."""
    if seed is not None:
        random.seed(seed)

    draws = home_wins = away_wins = goals = 0
    exact = Counter()
    blowouts = 0
    scorelines = Counter()
    point_counts = Counter()
    group_point_counts = defaultdict(Counter)

    teams_by_group = defaultdict(set)
    for entry in match_table:
        teams_by_group[entry['group']].update((entry['home'], entry['away']))

    total_matches = runs * len(match_table)
    for _ in range(runs):
        points = defaultdict(int)
        for entry in match_table:
            hg, ag = simulate_match(
                entry['eff_home'], entry['eff_away'],
                params['base_goals_per_team'], params['elo_scale'],
                params['draw_bias'], params['parity_scale'],
                params['elo_lambda_scale'])
            goals += hg + ag
            scorelines[(hg, ag)] += 1
            if (hg, ag) in ((0, 0), (1, 1), (2, 2)):
                exact[(hg, ag)] += 1
            if abs(hg - ag) >= 3:
                blowouts += 1
            if hg > ag:
                home_wins += 1
                points[entry['home']] += 3
            elif hg == ag:
                draws += 1
                points[entry['home']] += 1
                points[entry['away']] += 1
            else:
                away_wins += 1
                points[entry['away']] += 3

        for gid, teams in teams_by_group.items():
            for code in teams:
                pts = points[code]
                point_counts[pts] += 1
                group_point_counts[gid][pts] += 1

    total_teams = runs * sum(len(t) for t in teams_by_group.values())
    points_global = {
        str(p): round(100 * point_counts.get(p, 0) / total_teams, 2)
        for p in POSSIBLE_POINTS
    }
    points_by_group = {
        gid: {
            str(p): round(100 * counts.get(p, 0) / (runs * len(teams_by_group[gid])), 2)
            for p in POSSIBLE_POINTS
        }
        for gid, counts in sorted(group_point_counts.items())
    }
    intermediate_mass = round(sum(points_global[str(p)] for p in INTERMEDIATE_POINTS), 2)

    return {
        'draw_rate':          round(draws / total_matches, 4),
        'home_win_rate':      round(home_wins / total_matches, 4),
        'away_win_rate':      round(away_wins / total_matches, 4),
        'goals_per_match':    round(goals / total_matches, 3),
        'goals_per_team':     round(goals / (2 * total_matches), 3),
        'zero_zero_rate':     round(exact[(0, 0)] / total_matches, 4),
        'one_one_rate':       round(exact[(1, 1)] / total_matches, 4),
        'two_two_rate':       round(exact[(2, 2)] / total_matches, 4),
        'blowout_3plus_rate': round(blowouts / total_matches, 4),
        'most_common_scorelines': [
            {'score': f'{ga}-{gb}', 'pct': round(100 * c / total_matches, 2)}
            for (ga, gb), c in scorelines.most_common(10)
        ],
        'points_distribution_global': points_global,
        'points_distribution_by_group': points_by_group,
        'intermediate_points_mass_pct': intermediate_mass,
        'decisive_points_mass_pct': round(100 - intermediate_mass, 2),
    }


def range_penalty(value, low, high):
    """0 inside [low, high]; squared normalized distance outside."""
    span = max(high - low, 1e-9)
    if value < low:
        return ((low - value) / span) ** 2
    if value > high:
        return ((value - high) / span) ** 2
    return 0.0


def score_combination(summary):
    penalty = 0.0
    for metric, (low, high) in TARGETS.items():
        penalty += range_penalty(summary[metric], low, high)
    # Favoritism guard: a globally flat model is as bad as a binary one.
    if summary['favorite_win_rate'] < 0.45:
        penalty += ((0.45 - summary['favorite_win_rate']) / 0.05) ** 2
    return round(penalty, 4)


def run_grid_search(match_table, base_params, grid_runs, seed):
    results = []
    for base_goals in GRID_BASE_GOALS:
        for lambda_scale in GRID_LAMBDA_SCALE:
            for draw_bias in GRID_DRAW_BIAS:
                params = dict(base_params)
                params['base_goals_per_team'] = base_goals
                params['elo_lambda_scale'] = lambda_scale
                params['draw_bias'] = draw_bias
                summary, _ = analytic_report(match_table, params)
                results.append({
                    'base_goals_per_team': base_goals,
                    'elo_lambda_scale': lambda_scale,
                    'draw_bias': draw_bias,
                    'penalty': score_combination(summary),
                    'draw_rate': summary['draw_rate'],
                    'goals_per_match': summary['goals_per_match'],
                    'zero_zero_rate': summary['zero_zero_rate'],
                    'one_one_rate': summary['one_one_rate'],
                    'blowout_3plus_rate': summary['blowout_3plus_rate'],
                    'favorite_win_rate': summary['favorite_win_rate'],
                })

    results.sort(key=lambda r: (r['penalty'],
                                abs(r['draw_rate'] - 0.275),
                                abs(r['goals_per_match'] - 2.55)))

    # MC points-distribution check only for the analytic finalists.
    for row in results[:5]:
        params = dict(base_params)
        params['base_goals_per_team'] = row['base_goals_per_team']
        params['elo_lambda_scale'] = row['elo_lambda_scale']
        params['draw_bias'] = row['draw_bias']
        mc = monte_carlo_report(match_table, params, grid_runs, seed)
        row['intermediate_points_mass_pct'] = mc['intermediate_points_mass_pct']
        row['points_distribution_global'] = mc['points_distribution_global']
    return results


def print_summary(label, summary):
    print(f"\n{label}")
    print("-" * len(label))
    print(f"  draw_rate            {100 * summary['draw_rate']:5.1f}%   target 24-31%")
    print(f"  home/away win rate   {100 * summary['home_win_rate']:5.1f}% / {100 * summary['away_win_rate']:.1f}%")
    print(f"  goals_per_match      {summary['goals_per_match']:5.2f}    target 2.3-2.8")
    print(f"  goals_per_team       {summary['goals_per_team']:5.2f}")
    print(f"  0-0 rate             {100 * summary['zero_zero_rate']:5.1f}%   target 5-10%")
    print(f"  1-1 rate             {100 * summary['one_one_rate']:5.1f}%   target 8-14%")
    print(f"  2-2 rate             {100 * summary['two_two_rate']:5.1f}%")
    print(f"  blowout 3+ rate      {100 * summary['blowout_3plus_rate']:5.1f}%   target <=18%")
    if 'favorite_win_rate' in summary:
        print(f"  favorite win rate    {100 * summary['favorite_win_rate']:5.1f}%")
    print("  top scorelines:      " + ", ".join(
        f"{row['score']} ({row['pct']}%)" for row in summary['most_common_scorelines'][:6]))


def main():
    parser = argparse.ArgumentParser(description='Group-stage engine calibration report')
    parser.add_argument('--runs', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--output', default=None,
                        help='Optional JSON output path (keep out of git)')
    parser.add_argument('--grid', action='store_true', help='Run parameter grid search')
    parser.add_argument('--grid-runs', type=int, default=1000)
    parser.add_argument('--base-goals', type=float, default=None)
    parser.add_argument('--elo-lambda-scale', type=float, default=None)
    parser.add_argument('--draw-bias', type=float, default=None)
    parser.add_argument('--parity-scale', type=float, default=None)
    args = parser.parse_args()

    weights = load_weights()
    params = {
        'base_goals_per_team': args.base_goals if args.base_goals is not None else weights.get('base_goals_per_team', 1.3),
        'elo_scale': weights.get('elo_scale', 400),
        'elo_lambda_scale': args.elo_lambda_scale if args.elo_lambda_scale is not None else weights.get('elo_lambda_scale'),
        'draw_bias': args.draw_bias if args.draw_bias is not None else weights.get('draw_bias', 0.0),
        'parity_scale': args.parity_scale if args.parity_scale is not None else weights.get('parity_scale', 600.0),
    }
    xi_matchup_weight = weights.get('xi_matchup_weight', 0.20)

    matches = load_matches()
    strengths = load_strengths()
    xi_profiles = load_xi_profiles()
    match_table = build_match_table(matches, strengths, xi_profiles, xi_matchup_weight)

    print(f"Parameters: {params}")

    if args.grid:
        print(f"Grid search: {len(GRID_BASE_GOALS) * len(GRID_LAMBDA_SCALE) * len(GRID_DRAW_BIAS)} "
              f"combinations (analytic) + MC ({args.grid_runs} runs) for the top 5")
        results = run_grid_search(match_table, params, args.grid_runs, args.seed)
        print(f"\n{'base':>5} {'scale':>6} {'bias':>5} {'penalty':>8} {'draw%':>6} "
              f"{'gls/m':>6} {'0-0%':>5} {'1-1%':>5} {'blw%':>5} {'fav%':>5} {'mid-pts%':>8}")
        for row in results[:15]:
            mid = row.get('intermediate_points_mass_pct')
            print(f"{row['base_goals_per_team']:>5.2f} {row['elo_lambda_scale']:>6.0f} "
                  f"{row['draw_bias']:>5.2f} {row['penalty']:>8.4f} "
                  f"{100 * row['draw_rate']:>6.1f} {row['goals_per_match']:>6.2f} "
                  f"{100 * row['zero_zero_rate']:>5.1f} {100 * row['one_one_rate']:>5.1f} "
                  f"{100 * row['blowout_3plus_rate']:>5.1f} {100 * row['favorite_win_rate']:>5.1f} "
                  f"{mid if mid is not None else '':>8}")
        if args.output:
            Path(args.output).write_text(
                json.dumps({'grid_results': results, 'targets': TARGETS}, indent=2),
                encoding='utf-8')
            print(f"\nSaved grid results -> {args.output}")
        return

    analytic, per_match = analytic_report(match_table, params)
    print_summary("Analytic (exact, from adjusted score matrices)", analytic)

    print(f"\nRunning Monte Carlo ({args.runs} runs, seed={args.seed})...")
    simulated = monte_carlo_report(match_table, params, args.runs, args.seed)
    print_summary("Simulated (Monte Carlo)", simulated)

    print("\nGlobal points distribution (% of team-tournaments):")
    for p in POSSIBLE_POINTS:
        pct = simulated['points_distribution_global'][str(p)]
        bar = '#' * int(round(pct))
        print(f"  {p:>2} pts  {pct:6.2f}%  {bar}")
    print(f"  Mass on intermediate points (1,2,4,5,7): {simulated['intermediate_points_mass_pct']}%")

    report = {
        'runs': args.runs,
        'seed': args.seed,
        'parameters': params,
        'targets': {k: list(v) for k, v in TARGETS.items()},
        'analytic': analytic,
        'simulated': simulated,
        'top_unbalanced_matches': top_matches(per_match, 'p_favorite'),
        'top_draw_prone_matches': top_matches(per_match, 'p_draw'),
    }

    print("\nTop 10 most unbalanced fixtures (analytic):")
    for row in report['top_unbalanced_matches']:
        print(f"  {row['match_id']:18s} {row['home']:>4} {row['p_home']:.0%} / "
              f"E {row['p_draw']:.0%} / {row['away']:>4} {row['p_away']:.0%}")
    print("\nTop 10 most draw-prone fixtures (analytic):")
    for row in report['top_draw_prone_matches']:
        print(f"  {row['match_id']:18s} {row['home']:>4} {row['p_home']:.0%} / "
              f"E {row['p_draw']:.0%} / {row['away']:>4} {row['p_away']:.0%}")

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"\nSaved report -> {args.output}")


if __name__ == '__main__':
    main()
