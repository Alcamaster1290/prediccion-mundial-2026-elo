#!/usr/bin/env python3
"""simulate_group_stage.py -- Single simulation of the 2026 World Cup group stage.

Importable: from simulate_group_stage import simulate_all_groups, load_matches, load_strengths
Standalone: python scripts/simulate_group_stage.py [--seed 42]

Algorithm:
  - Team strength score = ELO-based value from team_strength_snapshots.json
  - Goals per team drawn from Poisson(lambda), where lambda = base_goals * 10^(diff/800)
  - 10^(diff/800) is the square root of the standard ELO win probability ratio
  - Group standings: PTS -> DG -> GF -> draw_order (GROUP_TEAMS index)
"""
import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

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


def poisson_goals(lam):
    """Knuth algorithm: Poisson random variate for goal count."""
    L = math.exp(-max(lam, 0.01))
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def match_lambdas(strength_a, strength_b, base_goals_per_team):
    """Returns (lambda_a, lambda_b) using ELO ratio method.

    lambda_a / lambda_b = 10^(diff/400), same ratio as win probability.
    Both lambdas multiply to base_goals_per_team^2 (geometric mean preserved).
    """
    diff = strength_a - strength_b
    # sqrt of win-probability ratio keeps geometric mean constant
    factor = 10 ** (diff / 800)
    lambda_a = base_goals_per_team * factor
    lambda_b = base_goals_per_team / factor
    return lambda_a, lambda_b


def simulate_match(home_strength, away_strength, base_goals):
    la, lb = match_lambdas(home_strength, away_strength, base_goals)
    return poisson_goals(la), poisson_goals(lb)


def simulate_group(group_id, group_matches, strengths, base_goals):
    """Simulate 6 matches and return ranked team list (4 items)."""
    draw_order = GROUP_ORDER.get(group_id.upper(), [])
    stats = defaultdict(lambda: {'PJ':0,'PG':0,'PE':0,'PP':0,'GF':0,'GC':0,'DG':0,'PTS':0})

    for m in group_matches:
        h, a = m['home_team'], m['away_team']
        sh = strengths.get(h, 1600)
        sa = strengths.get(a, 1600)
        hg, ag = simulate_match(sh, sa, base_goals)

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


def simulate_all_groups(matches, strengths, base_goals):
    """Run one full group stage simulation. Returns {group_id: [ranked_teams]}."""
    by_group = defaultdict(list)
    for m in matches:
        by_group[m['group']].append(m)

    return {
        gid: simulate_group(gid, gmatches, strengths, base_goals)
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

    matches   = load_matches()
    strengths = load_strengths()

    standings = simulate_all_groups(matches, strengths, base_goals)

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
