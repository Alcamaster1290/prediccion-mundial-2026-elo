#!/usr/bin/env python3
"""validate_data.py — Validates groups.json, matches.json, and match_context.json.

Run: python scripts/validate_data.py
Exit 0 = all checks passed, 1 = failures found.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

EXPECTED_GROUPS = list('ABCDEFGHIJKL')
EXPECTED_FIXTURES_PER_GROUP = 6
EXPECTED_TOTAL_MATCHES = 72


def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"FAIL JSON parse error in {path}: {e}")
        sys.exit(1)


def check_groups(data):
    errors = []
    groups = data.get('groups', [])

    if len(groups) != 12:
        errors.append(f"Expected 12 groups, got {len(groups)}")

    group_ids = {g['id'] for g in groups}
    for gid in EXPECTED_GROUPS:
        if gid not in group_ids:
            errors.append(f"Missing group {gid}")

    for g in groups:
        fixtures = g.get('fixtures', [])
        if len(fixtures) != EXPECTED_FIXTURES_PER_GROUP:
            errors.append(f"Group {g['id']}: expected {EXPECTED_FIXTURES_PER_GROUP} fixtures, got {len(fixtures)}")
        teams = g.get('teams', [])
        if len(teams) != 4:
            errors.append(f"Group {g['id']}: expected 4 teams, got {len(teams)}")
        for f in fixtures:
            if f.get('home') not in teams or f.get('away') not in teams:
                errors.append(f"Group {g['id']}: fixture {f.get('home')} vs {f.get('away')} has team not in group {teams}")

    return errors


def check_matches(data):
    errors = []

    if len(data) != EXPECTED_TOTAL_MATCHES:
        errors.append(f"Expected {EXPECTED_TOTAL_MATCHES} matches, got {len(data)}")

    match_ids = [m['match_id'] for m in data]
    if len(match_ids) != len(set(match_ids)):
        dupes = [mid for mid in match_ids if match_ids.count(mid) > 1]
        errors.append(f"Duplicate match_ids: {list(set(dupes))}")

    match_nums = [m['match_number'] for m in data]
    expected_nums = list(range(1, EXPECTED_TOTAL_MATCHES + 1))
    if sorted(match_nums) != expected_nums:
        errors.append(f"match_number sequence is not 1-{EXPECTED_TOTAL_MATCHES}")

    for m in data:
        for field in ('match_id', 'match_number', 'group', 'jornada', 'date', 'home_team', 'away_team'):
            if field not in m:
                errors.append(f"Match {m.get('match_number', '?')}: missing field '{field}'")
        mid = m.get('match_id', '')
        if mid and not mid.startswith('grp-'):
            errors.append(f"Match {m.get('match_number')}: match_id '{mid}' should start with 'grp-'")

    return errors


def check_match_context(entries, match_ids_set):
    errors = []
    warnings = []

    for entry in entries:
        mid = entry.get('match_id', '')
        if mid not in match_ids_set:
            warnings.append(f"  WARN match_context '{mid}' not in matches.json")
        for side in ('team_a_context', 'team_b_context'):
            ctx = entry.get(side, {})
            if 'elo_intl' not in ctx:
                errors.append(f"match_context '{mid}' {side}: missing elo_intl")

    return errors, warnings


def main():
    ok = True

    # groups.json
    groups_data = load_json(REPO_ROOT / 'data' / 'groups.json')
    if groups_data is None:
        print("FAIL data/groups.json not found")
        sys.exit(1)

    errs = check_groups(groups_data)
    if errs:
        for e in errs:
            print(f"FAIL [groups.json] {e}")
        ok = False
    else:
        print("PASS data/groups.json -- 12 groups, 72 fixtures, all teams valid")

    # matches.json
    matches_data = load_json(REPO_ROOT / 'data' / 'matches.json')
    if matches_data is None:
        print("SKIP data/matches.json -- not found; run: python scripts/generate_matches.py")
    else:
        errs = check_matches(matches_data)
        if errs:
            for e in errs:
                print(f"FAIL [matches.json] {e}")
            ok = False
        else:
            print(f"PASS data/matches.json -- {len(matches_data)} matches, IDs unique, numbers 1-{EXPECTED_TOTAL_MATCHES}")

        # match_context.json cross-reference
        ctx_raw = load_json(REPO_ROOT / 'data' / 'match_context.json')
        if ctx_raw is None:
            print("SKIP data/match_context.json -- not found")
        else:
            entries = ctx_raw.get('matches', ctx_raw) if isinstance(ctx_raw, dict) else ctx_raw
            match_ids_set = {m['match_id'] for m in matches_data}
            errs, warns = check_match_context(entries, match_ids_set)
            for w in warns:
                print(w)
            if errs:
                for e in errs:
                    print(f"FAIL [match_context.json] {e}")
                ok = False
            else:
                print(f"PASS data/match_context.json -- {len(entries)} entries, elo_intl present")

    # model_weights.json
    weights = load_json(REPO_ROOT / 'data' / 'model_weights.json')
    if weights is None:
        print("SKIP data/model_weights.json -- not found")
    else:
        w_sum = weights.get('elo_intl_weight', 0) + weights.get('xi_club_blend_weight', 0)
        if abs(w_sum - 1.0) > 0.001:
            print(f"FAIL [model_weights.json] weights sum to {w_sum:.3f} (expected 1.0)")
            ok = False
        else:
            print(f"PASS data/model_weights.json -- weights sum to {w_sum:.2f}")

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
