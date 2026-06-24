import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_predictions as gp  # noqa: E402


@pytest.fixture
def generated_prediction_sql(tmp_path, monkeypatch):
    strengths_path = tmp_path / "team_strength_snapshots.json"
    output_sql = tmp_path / "predictions_seed.sql"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_team_strength.py",
            "--output",
            str(strengths_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    monkeypatch.setattr(gp, "STRENGTHS_FILE", strengths_path)
    monkeypatch.setattr(gp, "OUTPUT_SQL", output_sql)
    gp.main()
    return output_sql.read_text(encoding="utf-8")


def load_matches():
    return json.loads((REPO_ROOT / "data/matches.json").read_text(encoding="utf-8"))


def match_by_id(matches, match_id):
    return next(match for match in matches if match["match_id"] == match_id)


def helper(name):
    assert hasattr(gp, name)
    return getattr(gp, name)


def test_calendar_notes_cover_debut_second_match_and_group_closure():
    matches = load_matches()
    build_group_fixture_index = helper("build_group_fixture_index")
    build_calendar_note = helper("build_calendar_note")
    fixture_index = build_group_fixture_index(matches)

    j1_note = build_calendar_note(match_by_id(matches, "grp-a-j1-kor-cze"), fixture_index)
    j2_note = build_calendar_note(match_by_id(matches, "grp-a-j2-mex-kor"), fixture_index)
    j3_note = build_calendar_note(match_by_id(matches, "grp-a-j3-cze-mex"), fixture_index)

    assert "debut" in j1_note.lower()
    assert "segunda jornada" in j2_note.lower()
    assert "cerrará el grupo" in j2_note.lower()
    assert "cierre" in j3_note.lower()
    assert "simultáneo" in j3_note.lower()
    assert "diferencia de goles" in j3_note.lower()


def test_prediction_explanation_adds_probability_and_calendar_when_context_is_missing():
    build_probability_note = helper("build_probability_note")
    compose_prediction_explanation = helper("compose_prediction_explanation")
    match = {
        "home_name": "Belgica",
        "away_name": "Iran",
    }

    model_note = build_probability_note(match, 75.65, 15.53, 8.82)
    explanation = compose_prediction_explanation(
        "",
        model_note,
        "El calendario del debut obliga a construir margen antes de la segunda jornada.",
    )

    assert "Belgica" in explanation
    assert "%" not in explanation
    assert "75.7" not in explanation
    assert "El modelo ELO inclina la lectura" in explanation
    assert "calendario" in explanation.lower()


def test_prediction_explanation_keeps_base_context_and_adds_model_probability():
    build_probability_note = helper("build_probability_note")
    compose_prediction_explanation = helper("compose_prediction_explanation")
    match = {
        "home_name": "Qatar",
        "away_name": "Suiza",
    }

    model_note = build_probability_note(match, 0.69, 9.01, 90.30)
    explanation = compose_prediction_explanation(
        "Qatar puede competir si sostiene el bloque bajo.",
        model_note,
        "El calendario del debut condiciona la segunda jornada.",
    )

    assert explanation.startswith("Qatar puede competir")
    assert "El modelo ELO inclina la lectura hacia Suiza" in explanation
    assert "%" not in explanation
    assert "90.3" not in explanation
    assert "calendario" in explanation.lower()


def test_context_lookup_keeps_team_context_aligned_when_match_order_changes():
    build_context_lookup = helper("build_context_lookup")
    find_context_for_match = helper("find_context_for_match")
    context_for_team = helper("context_for_team")
    context_matches = [
        {
            "match_id": "grp-c-j3-bra-sco",
            "grupo": "C",
            "jornada": 3,
            "team_a": "bra",
            "team_b": "sco",
            "team_a_context": {"incentivo_competitivo": "Brasil busca liderato."},
            "team_b_context": {"incentivo_competitivo": "Escocia busca puntos."},
        }
    ]
    match = {
        "match_id": "grp-c-j3-sco-bra",
        "group": "C",
        "jornada": 3,
        "home_team": "sco",
        "away_team": "bra",
    }

    by_id, by_pair = build_context_lookup(context_matches)
    ctx = find_context_for_match(match, by_id, by_pair)

    assert context_for_team(ctx, "sco")["incentivo_competitivo"] == "Escocia busca puntos."
    assert context_for_team(ctx, "bra")["incentivo_competitivo"] == "Brasil busca liderato."


def test_player_factor_note_mentions_messi_without_solo_claim():
    build_player_profiles = helper("build_player_profiles")
    build_player_factor_note = helper("build_player_factor_note")
    teams_data = json.loads((REPO_ROOT / "data/teams.json").read_text(encoding="utf-8"))
    match = {
        "match_id": "grp-j-j2-arg-aut",
        "home_team": "arg",
        "away_team": "aut",
        "home_name": "Argentina",
        "away_name": "Austria",
    }

    note = build_player_factor_note(match, build_player_profiles(teams_data))

    assert note.startswith("Jugador diferencial.")
    assert "Lionel Messi" in note
    assert "atrae marcas" in note
    assert "%" not in note
    assert "puntos" not in note
    assert "solo" not in note.lower()


def test_argentina_austria_prediction_uses_xi_matchup_not_star_solo_claim(generated_prediction_sql):
    sql = generated_prediction_sql
    match_line = next(
        line for line in sql.splitlines()
        if "'grp-j-j2-arg-aut'" in line
    )

    assert "roce de club" in match_line
    assert "defensa" in match_line.lower()
    assert "mediocampo" in match_line.lower()
    assert "Jugador diferencial" in match_line
    assert "Lionel Messi" in match_line
    assert "resolver el partido solo" not in match_line.lower()
    assert "puede resolver él solo" not in match_line.lower()


def test_predictions_with_incomplete_xi_use_partial_data_notice(generated_prediction_sql):
    sql = generated_prediction_sql
    jordan_line = next(
        line for line in sql.splitlines()
        if "'grp-j-j3-jor-arg'" in line
    )

    assert "comparación de onces es parcial" in jordan_line
    assert "Jordania no tiene un once titular completo" in jordan_line
    assert "Messi puede" not in jordan_line
    assert "golea" not in jordan_line.lower()
