#!/usr/bin/env python3
"""simulate_group_stage.py -- Single simulation of the 2026 World Cup group stage.

Importable: from simulate_group_stage import simulate_all_groups, load_matches, load_strengths
Standalone: python scripts/simulate_group_stage.py [--seed 42]

Algorithm:
  - Team strength score = ELO-based value from team_strength_snapshots.json
  - ELO difference defines expected goal share through the standard expected-score curve
  - Goals per team drawn from Poisson(lambda), keeping total expected goals stable
  - Group standings: PTS -> DG -> GF -> draw_order (GROUP_TEAMS index)
"""
import argparse
import bisect
import json
import math
import random
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from elo_probability import (
    adjust_result_probabilities_for_draw,
    match_lambdas as elo_match_lambdas,
    poisson_pmf,
)
from xi_matchups import build_xi_profiles, matchup_adjusted_strengths

REPO_ROOT = Path(__file__).parent.parent

# Official draw/pot order for each group (same as standings.js GROUP_TEAMS)
GROUP_ORDER = {
    'A': ['mex','zaf','kor','cze'],
    'B': ['can','bih','qat','sui'],
    'C': ['bra','mar','hti','sco'],
    'D': ['usa','pry','aus','tur'],
    'E': ['ger','cuw','civ','ecu'],
    'F': ['ned','jpn','swe','tun'],
    'G': ['bel','egy','irn','nzl'],
    'H': ['esp','cpv','ksa','ury'],
    'I': ['fra','sen','irq','nor'],
    'J': ['arg','alg','aut','jor'],
    'K': ['por','cod','uzb','col'],
    'L': ['eng','cro','gha','pan'],
}


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_matches():
    return load_json(REPO_ROOT / 'data' / 'matches.json')


def load_strengths():
    data = load_json(REPO_ROOT / 'data' / 'team_strength_snapshots.json')
    return {code: t['strength_score'] for code, t in data['teams'].items()}


def load_xi_profiles():
    return build_xi_profiles(load_json(REPO_ROOT / 'data' / 'teams.json'))


def poisson_goals(lam):
    """Knuth algorithm: Poisson random variate for goal count."""
    L = math.exp(-max(lam, 0.01))
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def match_lambdas(strength_a, strength_b, base_goals_per_team, elo_scale=400,
                  elo_lambda_scale=None):
    """Returns (lambda_a, lambda_b) using ELO ratio method.

    The ELO expected-score curve controls each team's expected goal share.
    Total expected goals stay fixed at 2 * base_goals_per_team.
    ``elo_lambda_scale`` (calibration v1.3) softens the goal split without
    touching the win-expectancy ``elo_scale``.
    """
    return elo_match_lambdas(strength_a, strength_b, base_goals_per_team,
                             elo_scale, elo_lambda_scale)


MAX_GRID_GOALS = 10


@lru_cache(maxsize=512)
def match_score_sampler(lambda_a, lambda_b, strength_diff, draw_bias, parity_scale):
    """Build a cached sampler table for one fixed match.

    Joint truncated Poisson score matrix whose win/draw/loss class masses are
    rescaled to match ``adjust_result_probabilities_for_draw``. Within each
    outcome class the relative scoreline probabilities are preserved. Returns
    (scores, cumulative_weights) ready for bisect sampling.
    """
    pmf_a = poisson_pmf(lambda_a, MAX_GRID_GOALS)
    pmf_b = poisson_pmf(lambda_b, MAX_GRID_GOALS)

    win_a = draw = win_b = 0.0
    cells = []
    for ga, pa in enumerate(pmf_a):
        for gb, pb in enumerate(pmf_b):
            p = pa * pb
            cells.append((ga, gb, p))
            if ga > gb:
                win_a += p
            elif ga == gb:
                draw += p
            else:
                win_b += p

    adj_a, adj_d, adj_b = adjust_result_probabilities_for_draw(
        win_a, draw, win_b, draw_bias, strength_diff, parity_scale)

    factor_a = adj_a / win_a if win_a > 0 else 0.0
    factor_d = adj_d / draw if draw > 0 else 0.0
    factor_b = adj_b / win_b if win_b > 0 else 0.0

    scores = []
    cumulative = []
    acc = 0.0
    for ga, gb, p in cells:
        factor = factor_a if ga > gb else (factor_d if ga == gb else factor_b)
        acc += p * factor
        scores.append((ga, gb))
        cumulative.append(acc)
    return tuple(scores), tuple(cumulative)


def simulate_match(home_strength, away_strength, base_goals, elo_scale=400,
                   draw_bias=0.0, parity_scale=600.0, elo_lambda_scale=None):
    la, lb = elo_match_lambdas(home_strength, away_strength, base_goals,
                               elo_scale, elo_lambda_scale)
    if draw_bias <= 0:
        # Legacy path: direct (untruncated) Poisson sampling.
        return poisson_goals(la), poisson_goals(lb)

    scores, cumulative = match_score_sampler(
        round(la, 6),
        round(lb, 6),
        round(home_strength - away_strength, 1),
        draw_bias,
        parity_scale,
    )
    r = random.random() * cumulative[-1]
    return scores[bisect.bisect_left(cumulative, r)]


def simulate_group(group_id, group_matches, strengths, base_goals, elo_scale=400, xi_profiles=None, xi_matchup_weight=0.20,
                   draw_bias=0.0, parity_scale=600.0, elo_lambda_scale=None):
    """Simulate 6 matches and return ranked team list (4 items)."""
    draw_order = GROUP_ORDER.get(group_id.upper(), [])
    stats = defaultdict(lambda: {'PJ':0,'PG':0,'PE':0,'PP':0,'GF':0,'GC':0,'DG':0,'PTS':0})

    for m in group_matches:
        h, a = m['home_team'], m['away_team']
        sh = strengths.get(h, 1600)
        sa = strengths.get(a, 1600)
        eff_h, eff_a, _ = matchup_adjusted_strengths(
            h,
            a,
            sh,
            sa,
            xi_profiles,
            xi_matchup_weight=xi_matchup_weight,
        )
        hg, ag = simulate_match(eff_h, eff_a, base_goals, elo_scale,
                                draw_bias, parity_scale, elo_lambda_scale)

        stats[h]['PJ'] += 1; stats[a]['PJ'] += 1
        stats[h]['GF'] += hg; stats[h]['GC'] += ag
        stats[a]['GF'] += ag; stats[a]['GC'] += hg
        stats[h]['DG'] = stats[h]['GF'] - stats[h]['GC']
        stats[a]['DG'] = stats[a]['GF'] - stats[a]['GC']

        if hg > ag:
            stats[h]['PG'] += 1; stats[h]['PTS'] += 3; stats[a]['PP'] += 1
        elif hg == ag:
            stats[h]['PE'] += 1; stats[h]['PTS'] += 1
            stats[a]['PE'] += 1; stats[a]['PTS'] += 1
        else:
            stats[a]['PG'] += 1; stats[a]['PTS'] += 3; stats[h]['PP'] += 1

    teams = list(stats.keys())
    teams.sort(key=lambda c: (
        -stats[c]['PTS'],
        -stats[c]['DG'],
        -stats[c]['GF'],
        draw_order.index(c) if c in draw_order else 99,
    ))

    return [{'code': c, **stats[c]} for c in teams]


def simulate_all_groups(matches, strengths, base_goals, elo_scale=400, xi_profiles=None, xi_matchup_weight=0.20,
                        draw_bias=0.0, parity_scale=600.0, elo_lambda_scale=None):
    """Run one full group stage simulation. Returns {group_id: [ranked_teams]}."""
    by_group = defaultdict(list)
    for m in matches:
        by_group[m['group']].append(m)

    return {
        gid: simulate_group(gid, gmatches, strengths, base_goals, elo_scale, xi_profiles, xi_matchup_weight,
                            draw_bias, parity_scale, elo_lambda_scale)
        for gid, gmatches in by_group.items()
    }


def best_thirds(standings):
    """Return the 12 third-place teams sorted by FIFA criteria."""
    thirds = []
    for gid, ranked in standings.items():
        if len(ranked) >= 3:
            t = dict(ranked[2])
            t['group'] = gid
            thirds.append(t)
    thirds.sort(key=lambda x: (-x['PTS'], -x['DG'], -x['GF']))
    return thirds


def main():
    parser = argparse.ArgumentParser(description='Simulate the group stage once')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    weights   = load_json(REPO_ROOT / 'data' / 'model_weights.json')
    base_goals = weights.get('base_goals_per_team', 1.3)
    elo_scale = weights.get('elo_scale', 400)
    xi_matchup_weight = weights.get('xi_matchup_weight', 0.20)
    draw_bias = weights.get('draw_bias', 0.0)
    parity_scale = weights.get('parity_scale', 600.0)
    elo_lambda_scale = weights.get('elo_lambda_scale')

    matches   = load_matches()
    strengths = load_strengths()
    xi_profiles = load_xi_profiles()

    standings = simulate_all_groups(matches, strengths, base_goals, elo_scale, xi_profiles, xi_matchup_weight,
                                    draw_bias, parity_scale, elo_lambda_scale)

    print("Group Stage Results")
    print("=" * 40)
    for gid in sorted(standings):
        print(f"\nGroup {gid}:")
        for i, t in enumerate(standings[gid]):
            marker = '+' if i < 2 else ('?' if i == 2 else ' ')
            print(f"  {marker} {i+1}. {t['code']:4s}  PTS:{t['PTS']}  GD:{t['DG']:+d}  GF:{t['GF']}")

    print("\nBest Thirds (top 8 qualify):")
    for i, t in enumerate(best_thirds(standings)):
        marker = 'Q' if i < 8 else '-'
        print(f"  {marker} {i+1}. {t['group']}/{t['code']:4s}  PTS:{t['PTS']}  GD:{t['DG']:+d}  GF:{t['GF']}")


if __name__ == '__main__':
    main()
