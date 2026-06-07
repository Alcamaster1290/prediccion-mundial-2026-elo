import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_predictions as gp  # noqa: E402


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
    assert "j3" in j2_note.lower()
    assert "cierre" in j3_note.lower()
    assert "simultaneo" in j3_note.lower()
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
        "Calendario: el debut obliga a construir margen antes de la segunda jornada.",
    )

    assert "Belgica" in explanation
    assert "75.7%" in explanation
    assert "Calendario:" in explanation


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
