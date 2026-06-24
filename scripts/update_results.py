#!/usr/bin/env python3
"""Update live results, rebuild conditioned Monte Carlo, and export the run."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from load_results import fetch_finished_results, write_fixed_results


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_RESULTS_PATH = REPO_ROOT / "data" / "fixed_results.json"
MC_RESULTS_PATH = REPO_ROOT / "data" / "mc_results.json"


def build_update_commands(python_executable, tokens, csv_path, sync_only, runs, seed, dry_run):
    commands = []
    if not sync_only:
        load_cmd = [python_executable, "scripts/load_results.py", *tokens]
        if csv_path:
            load_cmd.extend(["--csv", str(csv_path)])
        load_cmd.append("--yes")
        if dry_run:
            load_cmd.append("--dry-run")
        commands.append(load_cmd)

    commands.append([
        python_executable,
        "scripts/run_monte_carlo.py",
        "--runs",
        str(runs),
        "--seed",
        str(seed),
        "--fixed-results",
        "data/fixed_results.json",
        "--output",
        "data/mc_results.json",
    ])

    export_cmd = [
        python_executable,
        "scripts/export_to_supabase.py",
        "--mc-only",
        "--mc-results",
        "data/mc_results.json",
    ]
    if dry_run:
        export_cmd.append("--dry-run")
    commands.append(export_cmd)
    return commands


def run_step(command):
    print("$ " + " ".join(command))
    completed = subprocess.run(command, cwd=REPO_ROOT)
    return completed.returncode == 0


def sync_finished_results(path, dry_run=False):
    if dry_run:
        if not path.exists():
            write_fixed_results(path, {})
            print(f"Dry run: created empty {path.relative_to(REPO_ROOT)} for local simulation.")
        else:
            print(f"Dry run: using existing {path.relative_to(REPO_ROOT)}.")
        return True

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not service_key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        return False

    results = fetch_finished_results(supabase_url, service_key)
    write_fixed_results(path, results)
    print(f"Wrote {len(results)} finished group result(s) -> {path.relative_to(REPO_ROOT)}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Load results and refresh the conditioned Monte Carlo run")
    parser.add_argument("tokens", nargs="*", help="Result tokens like 25:2-1")
    parser.add_argument("--csv", dest="csv_path")
    parser.add_argument("--sync-only", action="store_true", help="Skip loading new scores and re-sync from Supabase")
    parser.add_argument("--runs", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.sync_only and not args.tokens and not args.csv_path:
        print("Provide result tokens/--csv, or pass --sync-only.")
        return 1

    strengths_path = REPO_ROOT / "data" / "team_strength_snapshots.json"
    if not strengths_path.exists():
        print(f"Run build_team_strength.py first: {strengths_path.relative_to(REPO_ROOT)} not found.")
        return 1

    commands = build_update_commands(
        python_executable=sys.executable,
        tokens=args.tokens,
        csv_path=args.csv_path,
        sync_only=args.sync_only,
        runs=args.runs,
        seed=args.seed,
        dry_run=args.dry_run,
    )

    if not args.sync_only:
        if not run_step(commands[0]):
            return 1

    if not sync_finished_results(FIXED_RESULTS_PATH, dry_run=args.dry_run):
        return 1

    start = 0 if args.sync_only else 1
    for command in commands[start:]:
        if not run_step(command):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
