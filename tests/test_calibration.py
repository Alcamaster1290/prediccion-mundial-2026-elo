"""Tests for the v1.3 calibration layer: draw bias, lambda scale and report."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from elo_probability import (  # noqa: E402
    adjust_result_probabilities_for_draw,
    match_lambdas,
)
from simulate_group_stage import match_score_sampler, simulate_match  # noqa: E402
from run_monte_carlo import run_monte_carlo  # noqa: E402
from calibration_report import (  # noqa: E402
    analytic_report,
    build_match_table,
    monte_carlo_report,
)


GROUP_MATCHES = [
    {"match_id": "grp-a-j1-mex-zaf", "group": "A", "home_team": "mex", "away_team": "zaf"},
    {"match_id": "grp-a-j1-kor-cze", "group": "A", "home_team": "kor", "away_team": "cze"},
    {"match_id": "grp-a-j2-mex-kor", "group": "A", "home_team": "mex", "away_team": "kor"},
    {"match_id": "grp-a-j2-cze-zaf", "group": "A", "home_team": "cze", "away_team": "zaf"},
    {"match_id": "grp-a-j3-kor-zaf", "group": "A", "home_team": "kor", "away_team": "zaf"},
    {"match_id": "grp-a-j3-mex-cze", "group": "A", "home_team": "mex", "away_team": "cze"},
]
STRENGTHS = {"mex": 1800, "zaf": 1500, "kor": 1700, "cze": 1650}


def test_adjusted_probabilities_sum_to_one_and_stay_non_negative():
    cases = [
        (0.40, 0.25, 0.35, 0.08, 0),
        (0.80, 0.15, 0.05, 0.10, 300),
        (0.05, 0.05, 0.90, 0.20, -700),
        (0.98, 0.01, 0.01, 0.20, 0),  # extreme bias against tiny decisive mass
    ]
    for p_a, p_d, p_b, bias, diff in cases:
        a, d, b = adjust_result_probabilities_for_draw(p_a, p_d, p_b, bias, diff, parity_scale=800)
        assert a >= 0 and d >= 0 and b >= 0
        assert round(a + d + b, 9) == 1.0


def test_draw_bias_boosts_even_matches_more_than_mismatches():
    base = (0.38, 0.26, 0.36)
    _, draw_even, _ = adjust_result_probabilities_for_draw(*base, 0.08, strength_diff=0, parity_scale=800)
    _, draw_uneven, _ = adjust_result_probabilities_for_draw(*base, 0.08, strength_diff=600, parity_scale=800)
    _, draw_out_of_range, _ = adjust_result_probabilities_for_draw(*base, 0.08, strength_diff=900, parity_scale=800)

    assert draw_even > draw_uneven > base[1]
    assert round(draw_out_of_range, 9) == base[1]  # beyond parity_scale: no boost


def test_draw_bias_takes_mass_proportionally_from_both_sides():
    p_a, p_d, p_b = 0.60, 0.20, 0.20
    a, d, b = adjust_result_probabilities_for_draw(p_a, p_d, p_b, 0.10, 0, parity_scale=800)
    removed_a = p_a - a
    removed_b = p_b - b
    assert d > p_d
    assert removed_a == pytest.approx(removed_b * (p_a / p_b))


def test_match_lambdas_respect_base_goals_and_lambda_scale():
    total = 2 * 1.25
    la_400, lb_400 = match_lambdas(2000, 1600, 1.25, elo_scale=400)
    la_800, lb_800 = match_lambdas(2000, 1600, 1.25, elo_scale=400, elo_lambda_scale=800)

    assert la_400 + lb_400 == pytest.approx(total)
    assert la_800 + lb_800 == pytest.approx(total)
    # Larger lambda scale softens the favorite's goal share
    assert la_400 > la_800 > lb_800 > lb_400
    # Without elo_lambda_scale the behavior matches the legacy elo_scale split
    assert match_lambdas(2000, 1600, 1.25, 400) == match_lambdas(2000, 1600, 1.25, 400, None)


def test_match_score_sampler_distribution_matches_adjusted_outcomes():
    la, lb = match_lambdas(1700, 1700, 1.25, 400, 800)
    scores, cumulative = match_score_sampler(round(la, 6), round(lb, 6), 0.0, 0.08, 800.0)
    total = cumulative[-1]
    prev = 0.0
    p_draw = 0.0
    for (ga, gb), cum in zip(scores, cumulative):
        if ga == gb:
            p_draw += (cum - prev) / total
        prev = cum
    assert 0.30 <= p_draw <= 0.40  # ~26% Poisson draw + 8% full-parity boost


def test_simulate_match_with_draw_bias_is_seedable_and_valid():
    import random

    random.seed(42)
    first = [simulate_match(1800, 1700, 1.25, 400, 0.08, 800, 800) for _ in range(20)]
    random.seed(42)
    second = [simulate_match(1800, 1700, 1.25, 400, 0.08, 800, 800) for _ in range(20)]

    assert first == second
    assert all(hg >= 0 and ag >= 0 for hg, ag in first)


def test_run_monte_carlo_points_pct_complete_and_sums_100_with_calibration():
    results, _ = run_monte_carlo(
        runs=30,
        seed=7,
        matches=GROUP_MATCHES,
        strengths=STRENGTHS,
        base_goals=1.25,
        elo_scale=400,
        draw_bias=0.08,
        parity_scale=800,
        elo_lambda_scale=800,
    )

    possible_points = ["0", "1", "2", "3", "4", "5", "6", "7", "9"]
    assert set(results) == set(STRENGTHS)
    for team_result in results.values():
        assert list(team_result["points_pct"]) == possible_points
        assert sum(team_result["points_pct"].values()) == 100.0


def test_calibration_report_runs_with_few_runs():
    params = {
        "base_goals_per_team": 1.25,
        "elo_scale": 400,
        "elo_lambda_scale": 800,
        "draw_bias": 0.08,
        "parity_scale": 800,
    }
    table = build_match_table(GROUP_MATCHES, STRENGTHS, {}, 0.2)
    analytic, per_match = analytic_report(table, params)
    simulated = monte_carlo_report(table, params, runs=25, seed=11)

    assert len(per_match) == len(GROUP_MATCHES)
    assert 0 < analytic["draw_rate"] < 1
    assert analytic["home_win_rate"] + analytic["draw_rate"] + analytic["away_win_rate"] == pytest.approx(1.0, abs=1e-6)
    points = simulated["points_distribution_global"]
    assert set(points) == {"0", "1", "2", "3", "4", "5", "6", "7", "9"}
    assert sum(points.values()) == pytest.approx(100.0, abs=0.1)
