import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_monte_carlo import run_monte_carlo  # noqa: E402


def test_run_monte_carlo_returns_points_distribution_for_each_team():
    matches = [
        {"group": "A", "home_team": "mex", "away_team": "zaf"},
        {"group": "A", "home_team": "kor", "away_team": "cze"},
        {"group": "A", "home_team": "mex", "away_team": "kor"},
        {"group": "A", "home_team": "cze", "away_team": "zaf"},
        {"group": "A", "home_team": "kor", "away_team": "zaf"},
        {"group": "A", "home_team": "mex", "away_team": "cze"},
    ]
    strengths = {"mex": 1800, "zaf": 1500, "kor": 1700, "cze": 1650}

    results, _ = run_monte_carlo(
        runs=20,
        seed=7,
        matches=matches,
        strengths=strengths,
        base_goals=1.3,
    )

    possible_points = ["0", "1", "2", "3", "4", "5", "6", "7", "9"]
    assert set(results) == set(strengths)
    for team_result in results.values():
        assert list(team_result["points_pct"]) == possible_points
        assert sum(team_result["points_pct"].values()) == 100.0
