#!/usr/bin/env python3
"""build_team_strength.py -- Calculates team strength scores for all 48 WC2026 teams.

ELO international source (primary):
  data/international_elo.json  (international-football.net, 2026-06-02)

Club ELO adjustment (only for teams analyzed in data/teams.json):
  xi_blend = average club ELO of titular players (from teams.json player list)

Strength formula:
  Analyzed teams:  score = elo_intl + (xi_blend - avg_xi_blend) * club_adj_weight
  All others:      score = elo_intl

Using a relative adjustment (delta from mean xi_blend) keeps the international ELO
scale intact and avoids the mismatch between the two rating systems.

Run: python scripts/build_team_strength.py [--output path]
"""
import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_intl_elos():
    data = load_json(REPO_ROOT / 'data' / 'international_elo.json')
    return {t['code']: {'elo': t['elo'], 'rank': t['rank'], 'name': t['name']}
            for t in data['teams']}


def calc_xi_blend_from_players(teams_data):
    """Average club ELO of titular players per team (from data/teams.json)."""
    xi_blend = {}
    for team in teams_data.get('teams', []):
        code = team['id']
        titular_elos = [
            p['elo'] for p in team.get('players', [])
            if p.get('titular') and p.get('elo') is not None
        ]
        if titular_elos:
            xi_blend[code] = round(sum(titular_elos) / len(titular_elos), 1)
    return xi_blend


def build_strengths(intl_elos, xi_blends, club_adj_weight):
    # Average xi_blend across all teams that have player data
    avg_xi = (sum(xi_blends.values()) / len(xi_blends)) if xi_blends else 0.0

    results = {}
    for code, intl in intl_elos.items():
        elo_intl = intl['elo']
        if code in xi_blends:
            # Relative adjustment: positive if above-average club quality, negative if below
            adj    = (xi_blends[code] - avg_xi) * club_adj_weight
            score  = round(elo_intl + adj, 1)
            method = 'xi_blend_adj'
        else:
            score  = float(elo_intl)
            method = 'elo_intl_only'
        results[code] = {
            'team_code':      code,
            'country_name':   intl['name'],
            'intl_rank':      intl['rank'],
            'elo_intl':       elo_intl,
            'xi_blend':       xi_blends.get(code),
            'avg_xi_blend':   round(avg_xi, 1) if xi_blends.get(code) is not None else None,
            'strength_score': score,
            'method':         method,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description='Build team strength snapshots')
    parser.add_argument(
        '--output',
        default=str(REPO_ROOT / 'data' / 'team_strength_snapshots.json'),
    )
    args = parser.parse_args()

    weights    = load_json(REPO_ROOT / 'data' / 'model_weights.json')
    teams_data = load_json(REPO_ROOT / 'data' / 'teams.json')
    intl_elos  = load_intl_elos()
    xi_blends  = calc_xi_blend_from_players(teams_data)

    club_adj_weight = weights.get('club_adj_weight', 0.35)
    strengths = build_strengths(intl_elos, xi_blends, club_adj_weight)

    output = {
        '_version':     weights.get('_version', '1.1'),
        '_rating_date': '2026-06-02',
        '_elo_source':  'international-football.net',
        '_formula':     'elo_intl + (xi_blend - avg_xi_blend) * club_adj_weight  [analyzed teams only]',
        '_weights':     {k: v for k, v in weights.items() if not k.startswith('_')},
        '_avg_xi_blend': round(sum(xi_blends.values()) / len(xi_blends), 1) if xi_blends else None,
        'teams':        strengths,
    }

    out_path = Path(args.output)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    xi_count  = sum(1 for v in strengths.values() if v['method'] == 'xi_blend_adj')
    intl_only = len(strengths) - xi_count
    avg_xi    = output['_avg_xi_blend']
    print(f"Built {len(strengths)} team strengths -> {out_path}")
    print(f"  {xi_count}  teams: xi_blend adjustment (avg_xi={avg_xi}, weight={club_adj_weight})")
    print(f"  {intl_only} teams: elo_intl only")
    print(f"\nTop 10 by strength score:")
    top10 = sorted(strengths.values(), key=lambda x: -x['strength_score'])[:10]
    for t in top10:
        adj_str = f"  adj:{t['strength_score'] - t['elo_intl']:+.1f}" if t['xi_blend'] else ''
        print(f"  {t['team_code']:4s}  intl:{t['elo_intl']:4d}  score:{t['strength_score']:7.1f}  [{t['method']}]{adj_str}")


if __name__ == '__main__':
    main()
