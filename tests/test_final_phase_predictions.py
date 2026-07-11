import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_final_phase_predictions  # noqa: E402


def run_generator():
    subprocess.run(
        [sys.executable, "scripts/generate_final_phase_predictions.py"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def load_predictions():
    path = REPO_ROOT / "data" / "final_phase_predictions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_final_phase_predictions_resolve_full_projected_bracket():
    run_generator()
    data = load_predictions()
    matches = data["matches"]

    assert data["source"]["fixed_count"] == 72
    assert len(matches) == 32
    assert [m["match_number"] for m in matches[:16]] == list(range(73, 89))
    assert all(m["home_team"] and m["away_team"] for m in matches)
    assert all(m["projected_winner"] in {m["home_team"], m["away_team"]} for m in matches)
    assert all(len(m["top_scorelines"]) == 10 for m in matches)
    assert all(round(m["advance_home_pct"] + m["advance_away_pct"], 1) == 100.0 for m in matches)


def test_final_phase_round_of_32_uses_finished_group_table():
    run_generator()
    matches = [m for m in load_predictions()["matches"] if m["phase"] == "r32"]
    r32 = {
        m["match_number"]: (m["home_team"], m["away_team"])
        for m in matches
    }
    labels = {
        m["match_number"]: m["away_label"]
        for m in matches
    }

    assert r32 == {
        73: ("zaf", "can"),
        74: ("ger", "pry"),
        75: ("ned", "mar"),
        76: ("bra", "jpn"),
        77: ("fra", "swe"),
        78: ("civ", "nor"),
        79: ("mex", "ecu"),
        80: ("eng", "cod"),
        81: ("usa", "bih"),
        82: ("bel", "sen"),
        83: ("por", "cro"),
        84: ("esp", "aut"),
        85: ("sui", "alg"),
        86: ("arg", "cpv"),
        87: ("col", "gha"),
        88: ("aus", "egy"),
    }
    assert labels[74] == "Mejor 3. Grupo D"
    assert labels[77] == "Mejor 3. Grupo F"
    assert labels[79] == "Mejor 3. Grupo E"
    assert labels[82] == "Mejor 3. Grupo I"
    assert labels[85] == "Mejor 3. Grupo J"


def test_final_phase_predictions_include_loaded_round_of_32_results():
    run_generator()
    data = load_predictions()
    matches = {match["match_number"]: match for match in data["matches"]}

    # Derivar los conteos de los resultados realmente cargados en lugar de
    # hardcodear un estado del torneo (avanza a medida que se cargan partidos).
    fixed = json.loads((REPO_ROOT / "data" / "fixed_results.json").read_text(encoding="utf-8"))["results"]
    knockout_count = sum(
        1 for key, value in fixed.items()
        if int(key) > 72 and isinstance(value, dict) and value.get("phase") != "group"
    )
    assert data["source"]["knockout_fixed_count"] == knockout_count
    assert data["source"]["finished_count"] == len(fixed)

    expected_results = {
        73: ("can", 0, 1, None, None),
        74: ("pry", 1, 1, 3, 4),
        75: ("mar", 1, 1, 2, 3),
        76: ("bra", 2, 1, None, None),
        77: ("fra", 3, 0, None, None),
        78: ("nor", 1, 2, None, None),
        79: ("mex", 2, 0, None, None),
    }
    for match_number, (winner, home_goals, away_goals, home_penalties, away_penalties) in expected_results.items():
        match = matches[match_number]
        assert match["status"] == "finished"
        assert match["actual_winner"] == winner
        assert match["projected_winner"] == winner
        assert match["home_goals"] == home_goals
        assert match["away_goals"] == away_goals
        if home_penalties is None:
            assert "home_penalties" not in match
            assert "away_penalties" not in match
        else:
            assert match["home_penalties"] == home_penalties
            assert match["away_penalties"] == away_penalties

    assert (matches[89]["home_team"], matches[89]["away_team"]) == ("pry", "fra")
    assert (matches[90]["home_team"], matches[90]["away_team"]) == ("can", "mar")
    assert (matches[91]["home_team"], matches[91]["away_team"]) == ("bra", "nor")
    assert (matches[92]["home_team"], matches[92]["away_team"]) == ("mex", "eng")


def test_final_phase_predictions_include_editorial_and_player_context():
    run_generator()
    matches = load_predictions()["matches"]

    for match in matches:
        # El editorial referencia el modelo ELO; el fraseo varía por cruce, así
        # que verificamos la mención "ELO" (no una plantilla literal fija).
        assert "ELO" in match["editorial"]
        assert match["player_factor"]
        assert "arquero" not in match["player_factor"].lower()
        assert "%" not in match["editorial"]


def test_final_phase_predictions_advance_actual_round_of_32_winner(tmp_path):
    fixed = json.loads((REPO_ROOT / "data" / "fixed_results.json").read_text(encoding="utf-8"))
    expected_knockout_count = len([
        value
        for key, value in fixed["results"].items()
        if int(key) > 72 and isinstance(value, dict) and value.get("phase") != "group"
    ])
    fixed["results"]["73"] = {
        "phase": "r32",
        "home_team": "zaf",
        "away_team": "can",
        "home_goals": 2,
        "away_goals": 1,
        "winner_team": "zaf",
    }
    fixed_path = tmp_path / "fixed_results.json"
    fixed_path.write_text(json.dumps(fixed), encoding="utf-8")

    data = generate_final_phase_predictions.build_final_predictions(fixed_results_path=fixed_path)
    matches = {match["match_number"]: match for match in data["matches"]}

    assert data["source"]["fixed_count"] == 72
    assert data["source"]["knockout_fixed_count"] == max(expected_knockout_count, 1)
    assert matches[73]["status"] == "finished"
    assert matches[73]["actual_winner"] == "zaf"
    assert matches[73]["projected_winner"] == "zaf"
    assert matches[90]["home_team"] == "zaf"


def test_final_phase_predictions_advance_penalty_winner(tmp_path):
    fixed = json.loads((REPO_ROOT / "data" / "fixed_results.json").read_text(encoding="utf-8"))
    fixed["results"]["73"] = {
        "phase": "r32",
        "home_team": "zaf",
        "away_team": "can",
        "home_goals": 1,
        "away_goals": 1,
        "home_penalties": 4,
        "away_penalties": 5,
        "winner_team": "can",
    }
    fixed_path = tmp_path / "fixed_results.json"
    fixed_path.write_text(json.dumps(fixed), encoding="utf-8")

    data = generate_final_phase_predictions.build_final_predictions(fixed_results_path=fixed_path)
    matches = {match["match_number"]: match for match in data["matches"]}

    assert matches[73]["home_penalties"] == 4
    assert matches[73]["away_penalties"] == 5
    assert matches[73]["actual_winner"] == "can"
    assert matches[90]["home_team"] == "can"
