import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    r32 = {
        m["match_number"]: (m["home_team"], m["away_team"])
        for m in load_predictions()["matches"]
        if m["phase"] == "r32"
    }

    assert r32 == {
        73: ("zaf", "can"),
        74: ("ger", "swe"),
        75: ("ned", "mar"),
        76: ("bra", "jpn"),
        77: ("fra", "pry"),
        78: ("civ", "nor"),
        79: ("mex", "ecu"),
        80: ("eng", "cod"),
        81: ("usa", "bih"),
        82: ("bel", "alg"),
        83: ("por", "cro"),
        84: ("esp", "aut"),
        85: ("sui", "sen"),
        86: ("arg", "cpv"),
        87: ("col", "gha"),
        88: ("aus", "egy"),
    }


def test_final_phase_predictions_include_editorial_and_player_context():
    run_generator()
    matches = load_predictions()["matches"]

    for match in matches:
        assert "modelo ELO" in match["editorial"]
        assert match["player_factor"]
        assert "arquero" not in match["player_factor"].lower()
        assert "%" not in match["editorial"]
