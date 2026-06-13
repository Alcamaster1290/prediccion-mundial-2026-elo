import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_monte_carlo import rounded_pct_distribution, run_monte_carlo  # noqa: E402
from simulate_group_stage import _fixed_score, load_fixed_results  # noqa: E402


GROUP_A_MATCHES = [
    {"group": "A", "match_number": 1, "home_team": "mex", "away_team": "zaf"},
    {"group": "A", "match_number": 2, "home_team": "kor", "away_team": "cze"},
    {"group": "A", "match_number": 3, "home_team": "mex", "away_team": "kor"},
    {"group": "A", "match_number": 4, "home_team": "cze", "away_team": "zaf"},
    {"group": "A", "match_number": 5, "home_team": "kor", "away_team": "zaf"},
    {"group": "A", "match_number": 6, "home_team": "mex", "away_team": "cze"},
]
GROUP_A_STRENGTHS = {"mex": 1800, "zaf": 1500, "kor": 1700, "cze": 1650}


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


def test_rounded_points_distribution_sums_to_100_after_rounding():
    distribution = rounded_pct_distribution({0: 1, 1: 1, 2: 1}, runs=3)

    assert sum(distribution.values()) == 100.0
    assert set(distribution) == {"0", "1", "2", "3", "4", "5", "6", "7", "9"}


def test_fixed_score_orientation_and_lookup():
    fixed = {7: {"home_team": "aus", "away_team": "tur", "home_goals": 2, "away_goals": 1}}
    # Misma orientación que el fixture
    assert _fixed_score(fixed, {"match_number": 7, "home_team": "aus", "away_team": "tur"}) == (2, 1)
    # Orientación invertida: se voltea el marcador
    assert _fixed_score(fixed, {"match_number": 7, "home_team": "tur", "away_team": "aus"}) == (1, 2)
    # No jugado / sin fijos
    assert _fixed_score(fixed, {"match_number": 99, "home_team": "x", "away_team": "y"}) is None
    assert _fixed_score(None, {"match_number": 7, "home_team": "aus", "away_team": "tur"}) is None


def test_fixed_results_condition_team_point_totals():
    # mex golea 5-0 a zaf en el partido fijo de cada simulación.
    fixed = {1: {"home_team": "mex", "away_team": "zaf", "home_goals": 5, "away_goals": 0}}
    results, _ = run_monte_carlo(
        runs=40, seed=3, matches=GROUP_A_MATCHES, strengths=GROUP_A_STRENGTHS,
        base_goals=1.3, fixed_results=fixed,
    )
    # mex gana siempre ese partido -> nunca termina con menos de 3 puntos
    assert results["mex"]["points_pct"]["0"] == 0.0
    assert results["mex"]["points_pct"]["1"] == 0.0
    assert results["mex"]["points_pct"]["2"] == 0.0
    # zaf pierde siempre ese partido -> tope de 6 puntos (no puede 7 ni 9)
    assert results["zaf"]["points_pct"]["7"] == 0.0
    assert results["zaf"]["points_pct"]["9"] == 0.0


def test_fixed_results_none_matches_unconditioned_run():
    # Sin fijos, el resultado es idéntico a no pasar el parámetro (compat).
    a, _ = run_monte_carlo(runs=25, seed=11, matches=GROUP_A_MATCHES,
                           strengths=GROUP_A_STRENGTHS, base_goals=1.3)
    b, _ = run_monte_carlo(runs=25, seed=11, matches=GROUP_A_MATCHES,
                           strengths=GROUP_A_STRENGTHS, base_goals=1.3, fixed_results={})
    assert a == b


def test_load_fixed_results_reads_finished_matches_from_mock():
    fixed = load_fixed_results()
    # El mock incluye USA 4-1 Paraguay (match 5, grupo D)
    assert 5 in fixed
    assert fixed[5] == {"home_team": "usa", "away_team": "pry", "home_goals": 4, "away_goals": 1}
