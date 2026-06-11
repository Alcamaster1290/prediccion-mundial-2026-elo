import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_predictions as gp  # noqa: E402
from elo_probability import top_scoreline_percentages  # noqa: E402
from simulate_group_stage import match_lambdas  # noqa: E402
from xi_matchups import build_xi_profiles, matchup_adjusted_strengths  # noqa: E402


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


def test_top_scorelines_are_sorted_and_consistent_with_match_probs():
    kwargs = dict(elo_scale=400, elo_lambda_scale=850, draw_bias=0.06, parity_scale=600.0)

    scorelines = top_scoreline_percentages(1800, 1650, 1.3, top_n=5, **kwargs)

    assert len(scorelines) == 5
    pcts = [item["pct"] for item in scorelines]
    assert pcts == sorted(pcts, reverse=True)
    assert all(0 < pct < 100 for pct in pcts)
    assert all(
        len(item["score"].split("-")) == 2
        and all(part.isdigit() for part in item["score"].split("-"))
        for item in scorelines
    )

    # La masa por clase de resultado debe respetar el 1X2 ajustado:
    # ningún marcador individual puede superar la probabilidad de su clase.
    pa, pd, pb = gp.match_probs(1800, 1650, 1.3, **kwargs)
    for item in scorelines:
        home, away = (int(part) for part in item["score"].split("-"))
        class_pct = pa if home > away else (pd if home == away else pb)
        assert item["pct"] <= class_pct


def test_top_scorelines_for_even_match_favor_draw_scores():
    scorelines = top_scoreline_percentages(
        1700, 1700, 1.3, elo_scale=400, draw_bias=0.06, top_n=3
    )

    home, away = (int(part) for part in scorelines[0]["score"].split("-"))
    assert home == away


def test_xi_profiles_compare_starter_lines_not_only_team_average():
    teams_data = {
        "teams": [
            {
                "id": "a",
                "players": [
                    {"name": "A GK", "pos": "GK", "elo": 1600, "titular": True},
                    {"name": "A DEF", "pos": "DEF", "elo": 1700, "titular": True},
                    {"name": "A MID", "pos": "MED", "elo": 1800, "titular": True},
                    {"name": "A FW", "pos": "DEL", "elo": 1900, "titular": True},
                ],
            },
            {
                "id": "b",
                "players": [
                    {"name": "B GK", "pos": "GK", "elo": 1500, "titular": True},
                    {"name": "B DEF", "pos": "DEF", "elo": 2000, "titular": True},
                    {"name": "B MID", "pos": "MED", "elo": 1500, "titular": True},
                    {"name": "B FW", "pos": "DEL", "elo": 1500, "titular": True},
                ],
            },
        ]
    }

    profiles = build_xi_profiles(teams_data)
    effective_a, effective_b, comparison = matchup_adjusted_strengths(
        "a",
        "b",
        1700,
        1700,
        profiles,
        xi_matchup_weight=0.25,
    )

    assert profiles["a"]["lines"]["attack"] == 1900
    assert profiles["b"]["lines"]["defense"] == 2000
    assert comparison["a"]["line_edges"]["attack_vs_defense"] == -100
    assert effective_a != 1700
    assert effective_b != 1700
