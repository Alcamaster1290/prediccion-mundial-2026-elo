import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_predictions as gp  # noqa: E402
from simulate_group_stage import match_lambdas  # noqa: E402


def test_prediction_lambdas_preserve_expected_total_goals():
    base_goals = 1.3

    favorite_lambda, underdog_lambda = match_lambdas(2000, 1600, base_goals)

    assert round(favorite_lambda + underdog_lambda, 6) == 2 * base_goals
    assert favorite_lambda > underdog_lambda
    assert favorite_lambda < 2 * base_goals
    assert underdog_lambda > 0


def test_generated_match_probs_are_deterministic_and_not_overconfident():
    first = gp.match_probs(2069.5, 1352.6, 1.3, elo_scale=400)
    second = gp.match_probs(2069.5, 1352.6, 1.3, elo_scale=400)

    assert first == second
    assert round(sum(first), 2) == 100.0
    assert first[0] < 95.0
    assert first[1] > 5.0
    assert first[2] > 0.0


def test_equal_strength_match_probs_are_symmetric_with_realistic_draw():
    home_win, draw, away_win = gp.match_probs(1700, 1700, 1.3, elo_scale=400)

    assert round(abs(home_win - away_win), 2) <= 0.01
    assert 24.0 <= draw <= 28.0
    assert round(home_win + draw + away_win, 2) == 100.0
