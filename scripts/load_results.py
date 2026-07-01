#!/usr/bin/env python3
"""Batch-load World Cup match results into Supabase.

Inline format:
  python scripts/load_results.py 25:2-1 26:0-0

CSV format:
  match_number,home_goals,away_goals
  25,2,1
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from export_to_supabase import supabase_request


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_TOKEN_RE = re.compile(r"^(\d+):(\d+)-(\d+)(?:p(\d+)-(\d+))?$")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_result_token(token):
    match = RESULT_TOKEN_RE.match(token.strip())
    if not match:
        raise ValueError(
            f"Invalid result token {token!r}; expected match_number:home-away or "
            "match_number:home-awayphomepens-awaypens, e.g. 25:2-1 or 73:1-1p4-3"
        )
    match_number, home_goals, away_goals, home_penalties, away_penalties = match.groups()
    values = (int(match_number), int(home_goals), int(away_goals))
    if home_penalties is None:
        return values
    return values + (int(home_penalties), int(away_penalties))


def parse_results_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"match_number", "home_goals", "away_goals"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        for line_number, row in enumerate(reader, start=2):
            token = f"{row.get('match_number', '').strip()}:{row.get('home_goals', '').strip()}-{row.get('away_goals', '').strip()}"
            if row.get("home_penalties") or row.get("away_penalties"):
                token += f"p{row.get('home_penalties', '').strip()}-{row.get('away_penalties', '').strip()}"
            try:
                rows.append(parse_result_token(token))
            except ValueError as exc:
                raise ValueError(f"Invalid CSV row {line_number}: {exc}") from exc
    return rows


def load_knockout_prediction_map(fixed_results_path=None):
    try:
        import generate_final_phase_predictions

        data = generate_final_phase_predictions.build_final_predictions(
            fixed_results_path=fixed_results_path or (REPO_ROOT / "data" / "fixed_results.json")
        )
    except Exception as exc:
        print(f"WARNING: could not resolve knockout teams locally: {exc}", file=sys.stderr)
        return {}
    return {
        int(match["match_number"]): match
        for match in data.get("matches", [])
        if match.get("match_number") is not None
    }


def load_fixture_matches(fixed_results_path=None):
    matches = []
    for item in load_json(REPO_ROOT / "data" / "matches.json"):
        row = dict(item)
        row["phase"] = "group"
        matches.append(row)
    knockout_projection = load_knockout_prediction_map(fixed_results_path)
    for item in load_json(REPO_ROOT / "data" / "knockout_matches.json"):
        projected = knockout_projection.get(int(item.get("matchNum")))
        matches.append({
            "match_number": item.get("matchNum"),
            "match_id": f"{item.get('phase')}-{item.get('matchNum')}",
            "phase": str(item.get("phase") or "").lower(),
            "group": None,
            "home_team": projected.get("home_team") if projected else None,
            "away_team": projected.get("away_team") if projected else None,
            "home_label": item.get("homeLabel"),
            "away_label": item.get("awayLabel"),
        })
    return matches


def unpack_parsed_result(parsed_row):
    if len(parsed_row) == 3:
        match_number, home_goals, away_goals = parsed_row
        return match_number, home_goals, away_goals, None, None
    if len(parsed_row) == 5:
        return parsed_row
    raise ValueError(f"Invalid parsed result shape for {parsed_row!r}")


def infer_winner(phase, home_team, away_team, home_goals, away_goals, home_penalties=None, away_penalties=None):
    if home_goals > away_goals:
        return home_team
    if away_goals > home_goals:
        return away_team
    if home_penalties is None and away_penalties is None:
        if phase != "group" and home_team and away_team:
            raise ValueError("Knockout draws require penalties, e.g. 73:1-1p4-3")
        return None
    if home_penalties is None or away_penalties is None:
        raise ValueError("Both penalty scores are required")
    if home_goals != away_goals:
        raise ValueError("Penalty scores are only valid when regular score is tied")
    if home_penalties == away_penalties:
        raise ValueError("Penalty shootout cannot end tied")
    return home_team if home_penalties > away_penalties else away_team


def validate_against_matches(parsed, matches):
    by_number = {int(m["match_number"]): m for m in matches if m.get("match_number") is not None}
    seen = set()
    rows = []

    for parsed_row in parsed:
        match_number, home_goals, away_goals, home_penalties, away_penalties = unpack_parsed_result(parsed_row)
        if match_number in seen:
            raise ValueError(f"Duplicate match_number {match_number} in input batch")
        seen.add(match_number)
        fixture = by_number.get(match_number)
        if fixture is None:
            raise ValueError(f"Unknown match_number {match_number}")

        home_team = fixture.get("home_team")
        away_team = fixture.get("away_team")
        phase = fixture.get("phase") or "group"
        winner_team = infer_winner(
            phase,
            home_team,
            away_team,
            home_goals,
            away_goals,
            home_penalties,
            away_penalties,
        )
        row = {
            "match_number": match_number,
            "phase": phase,
            "group_id": fixture.get("group_id") or fixture.get("group"),
            "match_id": fixture.get("match_id"),
            "home_team": home_team,
            "away_team": away_team,
            "home_label": fixture.get("home_name") or fixture.get("home_label"),
            "away_label": fixture.get("away_name") or fixture.get("away_label"),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "winner_team": winner_team,
        }
        if home_penalties is not None:
            row["home_penalties"] = home_penalties
        if away_penalties is not None:
            row["away_penalties"] = away_penalties
        rows.append(row)

    return rows


def build_patch(row, status="finished"):
    patch = {
        "home_goals": row["home_goals"],
        "away_goals": row["away_goals"],
        "status": status,
    }
    if row.get("phase") != "group":
        if row.get("home_team"):
            patch["home_team"] = row.get("home_team")
        if row.get("away_team"):
            patch["away_team"] = row.get("away_team")
    if row.get("home_penalties") is not None:
        patch["home_penalties"] = row.get("home_penalties")
    if row.get("away_penalties") is not None:
        patch["away_penalties"] = row.get("away_penalties")
    if status == "finished":
        patch["winner_team"] = row.get("winner_team")
    return patch


def apply_results(supabase_url, key, rows, status="finished", dry_run=False):
    if dry_run:
        return True

    for row in rows:
        path = f"match_results?match_number=eq.{row['match_number']}"
        err, _ = supabase_request(
            supabase_url,
            key,
            "PATCH",
            path,
            build_patch(row, status=status),
            prefer="return=minimal",
        )
        if err:
            print(f"ERROR updating match_results P{row['match_number']}: {err}")
            return False
    return True


def fetch_finished_results(supabase_url, key):
    path = (
        "match_results?status=eq.finished"
        "&select=match_number,phase,home_team,away_team,home_goals,away_goals,"
        "home_penalties,away_penalties,winner_team&order=match_number"
    )
    err, rows = supabase_request(supabase_url, key, "GET", path, prefer="return=representation")
    if err:
        raise RuntimeError(f"ERROR fetching finished match_results: {err}")

    results = {}
    for row in rows or []:
        match_number = row.get("match_number")
        if match_number is None or row.get("home_goals") is None or row.get("away_goals") is None:
            continue
        record = {
            "phase": row.get("phase"),
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "home_goals": int(row["home_goals"]),
            "away_goals": int(row["away_goals"]),
        }
        for field in ("home_penalties", "away_penalties"):
            if row.get(field) is not None:
                record[field] = int(row[field])
        if row.get("winner_team"):
            record["winner_team"] = row["winner_team"]
        results[int(match_number)] = record
    return results


def serialize_fixed_result(score):
    if isinstance(score, (list, tuple)):
        return [int(score[0]), int(score[1])]

    phase = score.get("phase")
    if phase == "group" or (
        phase is None
        and score.get("home_penalties") is None
        and score.get("away_penalties") is None
        and not score.get("winner_team")
    ):
        return [int(score["home_goals"]), int(score["away_goals"])]

    keep = (
        "phase",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "home_penalties",
        "away_penalties",
        "winner_team",
    )
    return {key: score[key] for key in keep if score.get(key) is not None}


def write_fixed_results(path, results):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "fetched_at": fetched_at,
        "results": {
            str(match_number): serialize_fixed_result(score)
            for match_number, score in sorted(results.items())
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_row(row, status):
    left = row.get("home_team") or row.get("home_label") or "home"
    right = row.get("away_team") or row.get("away_label") or "away"
    winner = row.get("winner_team") or "-"
    penalties = ""
    if row.get("home_penalties") is not None and row.get("away_penalties") is not None:
        penalties = f" p{row['home_penalties']}-{row['away_penalties']}"
    return (
        f"P{row['match_number']:>3}  {left} {row['home_goals']}-{row['away_goals']}{penalties} {right}"
        f"  -> {status}, winner={winner}"
    )


def require_env(dry_run=False):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if dry_run:
        return url or "https://dry-run.supabase.co", key or "dry-run-service-role"
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
    return url, key


def main():
    parser = argparse.ArgumentParser(description="Batch update public.match_results")
    parser.add_argument("tokens", nargs="*", help="Result tokens like 25:2-1")
    parser.add_argument("--csv", dest="csv_path", help="CSV with match_number,home_goals,away_goals")
    parser.add_argument("--status", default="finished", choices=["scheduled", "live", "finished", "postponed", "cancelled"])
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch finished group results into data/fixed_results.json")
    parser.add_argument("--fixed-results", default=str(REPO_ROOT / "data" / "fixed_results.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    try:
        supabase_url, key = require_env(dry_run=args.dry_run)

        if args.fetch_only:
            if args.dry_run:
                print(f"Dry run: would fetch finished results into {args.fixed_results}")
                return 0
            results = fetch_finished_results(supabase_url, key)
            write_fixed_results(args.fixed_results, results)
            print(f"Wrote {len(results)} finished group result(s) -> {args.fixed_results}")
            return 0

        parsed = [parse_result_token(token) for token in args.tokens]
        if args.csv_path:
            parsed.extend(parse_results_csv(Path(args.csv_path)))
        if not parsed:
            print("No results provided. Use tokens like 25:2-1, --csv, or --fetch-only.")
            return 1

        rows = validate_against_matches(parsed, load_fixture_matches(args.fixed_results))
        print("Results to apply:")
        for row in rows:
            print("  " + format_row(row, args.status))
        if not args.yes and not args.dry_run:
            answer = input("Apply these updates to Supabase? [y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled.")
                return 1

        if not apply_results(supabase_url, key, rows, status=args.status, dry_run=args.dry_run):
            return 1
        if args.dry_run:
            print("Dry run: no Supabase writes performed.")
            return 0

        results = fetch_finished_results(supabase_url, key)
        write_fixed_results(args.fixed_results, results)
        print(f"Applied {len(rows)} update(s). Wrote {len(results)} finished group result(s) -> {args.fixed_results}")
        return 0
    except (RuntimeError, ValueError) as exc:
        print(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
