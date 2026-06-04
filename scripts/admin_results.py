#!/usr/bin/env python3
"""admin_results.py - update one match result in Supabase.

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY. The service role key is read
from the environment only and must never be committed.
"""
import argparse
import json
import os
import sys

from export_to_supabase import supabase_request


def main():
    parser = argparse.ArgumentParser(description="Update public.match_results")
    parser.add_argument("match_number", type=int)
    parser.add_argument("--home-goals", type=int)
    parser.add_argument("--away-goals", type=int)
    parser.add_argument("--status", choices=["scheduled", "live", "finished", "postponed", "cancelled"])
    parser.add_argument("--winner-team")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    body = {}
    if args.home_goals is not None:
        body["home_goals"] = args.home_goals
    if args.away_goals is not None:
        body["away_goals"] = args.away_goals
    if args.status:
        body["status"] = args.status
    if args.winner_team:
        body["winner_team"] = args.winner_team

    if not body:
        print("Nothing to update.")
        return 1

    if args.dry_run:
        print(json.dumps({"match_number": args.match_number, "patch": body}, indent=2))
        return 0

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not service_key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        return 1

    path = f"match_results?match_number=eq.{args.match_number}"
    err, _ = supabase_request(supabase_url, service_key, "PATCH", path, body, prefer="return=minimal")
    if err:
        print(f"ERROR: {err}")
        return 1
    print(f"Updated match_results P{args.match_number}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
