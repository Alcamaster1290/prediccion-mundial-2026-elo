#!/usr/bin/env python3
"""build_team_strength.py -- Calculates team strength scores from ELO data.

Sources (in priority order):
  1. elo_intl from data/match_context.json (all 48 teams)
  2. elo_club_avg from match_context.json (teams with annotated squads)
  3. xi_club_blend from data/teams.json player list (teams with full squad data)

Strength formula when club data is available:
  score = elo_intl_weight * elo_intl + xi_club_blend_weight * elo_club_avg

Fallback (no club data):
  score = elo_intl

Run: python scripts/build_team_strength.py [--output path]
"""
import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def extract_intl_elos(ctx_raw):
    """Returns ({code: elo_intl}, {code: elo_club_avg}) from match_context."""
    entries = ctx_raw.get('matches', ctx_raw) if isinstance(ctx_raw, dict) else ctx_raw
    intl = {}
    club_avg = {}
    for entry in entries:
        for team_key, ctx_key in (('team_a', 'team_a_context'), ('team_b', 'team_b_context')):
            code = entry.get(team_key)
            ctx = entry.get(ctx_key, {})
            if code and code not in intl and 'elo_intl' in ctx:
                intl[code] = ctx['elo_intl']
            if code and code not in club_avg and 'elo_club_avg' in ctx:
                club_avg[code] = ctx['elo_club_avg']
    return intl, club_avg


def calc_xi_blend_from_players(teams_data):
    """Returns {code: avg_titular_elo} from teams.json squad lists."""
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


def build_strengths(intl_elos, club_avgs, xi_blends, weights):
    w_intl = weights.get('elo_intl_weight', 0.65)
    w_club = weights.get('xi_club_blend_weight', 0.35)

    results = {}
    for code, elo_intl in intl_elos.items():
        elo_club = club_avgs.get(code) or xi_blends.get(code)
        if elo_club is not None:
            score  = w_intl * elo_intl + w_club * elo_club
            method = 'weighted_blend'
        else:
            score  = float(elo_intl)
            method = 'elo_intl_only'
        results[code] = {
            'team_code':      code,
            'elo_intl':       elo_intl,
            'elo_club_avg':   elo_club,
            'strength_score': round(score, 1),
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
    ctx_raw    = load_json(REPO_ROOT / 'data' / 'match_context.json')
    teams_data = load_json(REPO_ROOT / 'data' / 'teams.json')

    intl_elos, club_avgs = extract_intl_elos(ctx_raw)
    xi_blends = calc_xi_blend_from_players(teams_data)

    strengths = build_strengths(intl_elos, club_avgs, xi_blends, weights)

    output = {
        '_version': weights.get('_version', '1.0'),
        '_weights': {k: v for k, v in weights.items() if not k.startswith('_')},
        'teams':    strengths,
    }

    out_path = Path(args.output)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    blend_count = sum(1 for v in strengths.values() if v['method'] == 'weighted_blend')
    print(f"Built {len(strengths)} team strengths -> {out_path}")
    print(f"  {blend_count} teams: weighted blend (elo_intl + club_avg)")
    print(f"  {len(strengths) - blend_count} teams: elo_intl only")


if __name__ == '__main__':
    main()
