#!/usr/bin/env python3
"""pipeline.py - runs the local data generation/export pipeline.

Default flow:
  validate -> generate_matches -> build_team_strength -> run_monte_carlo
  -> generate_predictions -> generate_seed_sql -> export_to_supabase

Use --skip-export for local generation only, or --dry-run to exercise export
without writing to Supabase.
"""
import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_step(command, dry_run=False):
    printable = " ".join(command)
    print(f"$ {printable}")
    if dry_run and command[-1] != "--dry-run":
        return True
    completed = subprocess.run(command, cwd=REPO_ROOT)
    return completed.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run Mundial 2026 data pipeline")
    parser.add_argument("--runs", type=int, default=10000, help="Monte Carlo iterations")
    parser.add_argument("--seed", type=int, default=42, help="Monte Carlo RNG seed")
    parser.add_argument("--skip-export", action="store_true", help="Do not write to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Show export payloads without Supabase writes")
    args = parser.parse_args()

    py = sys.executable
    steps = [
        [py, "scripts/validate_data.py"],
        [py, "scripts/generate_matches.py"],
        [py, "scripts/build_team_strength.py"],
        [py, "scripts/run_monte_carlo.py", "--runs", str(args.runs), "--seed", str(args.seed), "--output", "data/mc_results.json"],
        [py, "scripts/generate_predictions.py"],
        [py, "scripts/generate_seed_sql.py"],
    ]

    for step in steps:
        if not run_step(step):
            return 1

    if not args.skip_export:
        export_cmd = [py, "scripts/export_to_supabase.py", "--all"]
        if args.dry_run:
            export_cmd.append("--dry-run")
        if not run_step(export_cmd):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
