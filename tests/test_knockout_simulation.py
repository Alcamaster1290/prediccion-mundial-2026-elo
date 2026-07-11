"""Invariant checks for the knockout Monte Carlo (scripts/simulate_knockout.py).

BracketModel reads generated inputs that are gitignored (team_strength_snapshots
.json, fixed_results.json). When they are absent (clean checkout / CI) the tests
skip; when present (dev environment after a pipeline run) they assert the
probability invariants that must hold regardless of the random seed.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

REQUIRED = [
    DATA_DIR / "team_strength_snapshots.json",
    DATA_DIR / "fixed_results.json",
    DATA_DIR / "knockout_matches.json",
]

pytestmark = pytest.mark.skipif(
    not all(path.exists() for path in REQUIRED),
    reason="generated inputs (gitignored) not present",
)


@pytest.fixture(scope="module")
def result():
    from simulate_knockout import BracketModel, simulate

    model = BracketModel()
    teams, metrics = simulate(model, runs=5000, seed=7)
    return model, teams, metrics


def _by_code(teams):
    return {row["code"]: row for row in teams}


def test_champion_probabilities_sum_to_100(result):
    _, teams, _ = result
    total = sum(row["champion"] for row in teams)
    assert abs(total - 100.0) < 1.0


def test_two_finalists_so_reach_final_sums_to_200(result):
    _, teams, _ = result
    total = sum(row["reach_final"] for row in teams)
    assert abs(total - 200.0) < 1.0


def test_eliminated_teams_have_zero_forward_probability(result):
    model, teams, _ = result
    for row in teams:
        if row["code"] in model.eliminated:
            assert row["champion"] == 0.0
            assert row["reach_final"] == 0.0


def test_probabilities_are_monotonic_by_round(result):
    """A team cannot reach a later round more often than an earlier one."""
    _, teams, _ = result
    for row in teams:
        assert row["reach_r16"] >= row["reach_qf"] >= row["reach_sf"] >= row["reach_final"]
        assert row["reach_final"] >= row["champion"]


def test_determinism_same_seed(result):
    from simulate_knockout import BracketModel, simulate

    model, teams, _ = result
    teams_again, _ = simulate(model, runs=5000, seed=7)
    assert _by_code(teams_again) == _by_code(teams)


def test_decided_semifinalists_reach_sf_deterministically(result):
    """Teams that already won their quarterfinal are in the semis with prob 100."""
    model, teams, _ = result
    by_code = _by_code(teams)
    # Semifinalists whose slot is already decided by a fixed QF result.
    decided_sf = set()
    for info in model.feeders.values():
        if info["phase"] == "sf":
            for side in ("home", "away"):
                kind, ref = info[side]
                if kind == "W" and model.feeders.get(ref, {}).get("fixed_winner"):
                    decided_sf.add(model.feeders[ref]["fixed_winner"])
    for code in decided_sf:
        assert by_code[code]["reach_sf"] == 100.0
