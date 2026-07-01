import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import update_results  # noqa: E402


def test_build_update_commands_loads_results_then_runs_conditioned_mc_and_mc_only_export():
    commands = update_results.build_update_commands(
        python_executable="python",
        tokens=["25:2-1", "26:0-0"],
        csv_path=None,
        sync_only=False,
        runs=10000,
        seed=42,
        dry_run=False,
    )

    assert commands == [
        ["python", "scripts/load_results.py", "25:2-1", "26:0-0", "--yes"],
        [
            "python",
            "scripts/run_monte_carlo.py",
            "--runs",
            "10000",
            "--seed",
            "42",
            "--fixed-results",
            "data/fixed_results.json",
            "--output",
            "data/mc_results.json",
        ],
        ["python", "scripts/export_to_supabase.py", "--mc-only", "--mc-results", "data/mc_results.json"],
        ["python", "scripts/generate_final_phase_predictions.py"],
    ]


def test_build_update_commands_sync_only_skips_loader_and_keeps_dry_run_flag():
    commands = update_results.build_update_commands(
        python_executable="python",
        tokens=[],
        csv_path=None,
        sync_only=True,
        runs=500,
        seed=7,
        dry_run=True,
    )

    assert commands[0][1:] == [
        "scripts/run_monte_carlo.py",
        "--runs",
        "500",
        "--seed",
        "7",
        "--fixed-results",
        "data/fixed_results.json",
        "--output",
        "data/mc_results.json",
    ]
    assert commands[-1] == [
        "python",
        "scripts/generate_final_phase_predictions.py",
    ]
    assert commands[-2] == [
        "python",
        "scripts/export_to_supabase.py",
        "--mc-only",
        "--mc-results",
        "data/mc_results.json",
        "--dry-run",
    ]
