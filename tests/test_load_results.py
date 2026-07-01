import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_results  # noqa: E402


MATCHES = [
    {
        "match_number": 25,
        "match_id": "grp-a-j2-mex-kor",
        "group": "A",
        "home_team": "mex",
        "away_team": "kor",
        "home_name": "Mexico",
        "away_name": "Corea del Sur",
    },
    {
        "match_number": 73,
        "match_id": "r32-a-b",
        "phase": "r32",
        "home_team": None,
        "away_team": None,
        "home_label": "2. Grupo A",
        "away_label": "2. Grupo B",
    },
]


def test_parse_result_token_accepts_match_number_and_score():
    assert load_results.parse_result_token("25:2-1") == (25, 2, 1)


def test_parse_result_token_accepts_penalty_score_for_knockouts():
    assert load_results.parse_result_token("73:1-1p4-3") == (73, 1, 1, 4, 3)


def test_parse_result_token_rejects_bad_format_and_negative_scores():
    for token in ("25=2-1", "25:2", "25:-1-0", "abc:1-0"):
        try:
            load_results.parse_result_token(token)
        except ValueError as exc:
            assert token in str(exc)
        else:
            raise AssertionError(f"{token} should fail")


def test_parse_results_csv_reads_required_columns(tmp_path):
    csv_path = tmp_path / "results.csv"
    csv_path.write_text("match_number,home_goals,away_goals\n25,2,1\n73,0,0\n", encoding="utf-8")

    assert load_results.parse_results_csv(csv_path) == [(25, 2, 1), (73, 0, 0)]


def test_validate_against_matches_enriches_group_result_and_winner():
    rows = load_results.validate_against_matches([(25, 2, 1)], MATCHES)

    assert rows == [
        {
            "match_number": 25,
            "phase": "group",
            "group_id": "A",
            "match_id": "grp-a-j2-mex-kor",
            "home_team": "mex",
            "away_team": "kor",
            "home_label": "Mexico",
            "away_label": "Corea del Sur",
            "home_goals": 2,
            "away_goals": 1,
            "winner_team": "mex",
        }
    ]


def test_validate_against_matches_supports_knockout_labels_and_draw_without_winner():
    rows = load_results.validate_against_matches([(73, 0, 0)], MATCHES)

    assert rows[0]["phase"] == "r32"
    assert rows[0]["home_label"] == "2. Grupo A"
    assert rows[0]["away_label"] == "2. Grupo B"
    assert rows[0]["winner_team"] is None


def test_load_fixture_matches_resolves_round_of_32_teams_from_finished_groups():
    matches = load_results.load_fixture_matches()
    match = next(row for row in matches if row["match_number"] == 73)

    assert match["home_team"] == "zaf"
    assert match["away_team"] == "can"


def test_validate_against_matches_sets_knockout_winner_from_resolved_teams():
    matches = load_results.load_fixture_matches()

    rows = load_results.validate_against_matches([(73, 2, 1)], matches)

    assert rows[0]["home_team"] == "zaf"
    assert rows[0]["away_team"] == "can"
    assert rows[0]["winner_team"] == "zaf"


def test_validate_against_matches_uses_penalties_for_drawn_knockout():
    matches = load_results.load_fixture_matches()

    rows = load_results.validate_against_matches([(73, 1, 1, 4, 5)], matches)

    assert rows[0]["home_penalties"] == 4
    assert rows[0]["away_penalties"] == 5
    assert rows[0]["winner_team"] == "can"


def test_validate_against_matches_rejects_duplicate_or_unknown_match_numbers():
    for parsed in ([(99, 1, 0)], [(25, 1, 0), (25, 2, 0)]):
        try:
            load_results.validate_against_matches(parsed, MATCHES)
        except ValueError as exc:
            assert "match_number" in str(exc)
        else:
            raise AssertionError(f"{parsed} should fail")


def test_build_patch_sets_finished_status_and_winner():
    row = load_results.validate_against_matches([(25, 1, 3)], MATCHES)[0]

    assert load_results.build_patch(row) == {
        "home_goals": 1,
        "away_goals": 3,
        "status": "finished",
        "winner_team": "kor",
    }


def test_build_patch_includes_knockout_teams_and_penalties():
    row = load_results.validate_against_matches([(73, 1, 1, 4, 5)], load_results.load_fixture_matches())[0]

    assert load_results.build_patch(row) == {
        "home_team": "zaf",
        "away_team": "can",
        "home_goals": 1,
        "away_goals": 1,
        "home_penalties": 4,
        "away_penalties": 5,
        "status": "finished",
        "winner_team": "can",
    }


def test_apply_results_dry_run_does_not_call_network(monkeypatch):
    calls = []
    monkeypatch.setattr(load_results, "supabase_request", lambda *args, **kwargs: calls.append(args))

    ok = load_results.apply_results("https://example.supabase.co", "key", [{"match_number": 25}], dry_run=True)

    assert ok is True
    assert calls == []


def test_fetch_finished_results_normalizes_supabase_rows(monkeypatch):
    def fake_request(url, key, method, path, body=None, prefer="return=representation"):
        assert method == "GET"
        assert "status=eq.finished" in path
        assert "phase=eq.group" not in path
        return None, [
            {"match_number": 25, "phase": "group", "home_team": "mex", "away_team": "kor", "home_goals": 2, "away_goals": 1},
            {
                "match_number": 73,
                "phase": "r32",
                "home_team": "zaf",
                "away_team": "can",
                "home_goals": 1,
                "away_goals": 1,
                "home_penalties": 4,
                "away_penalties": 5,
                "winner_team": "can",
            },
            {"match_number": None, "home_goals": 1, "away_goals": 1},
        ]

    monkeypatch.setattr(load_results, "supabase_request", fake_request)

    assert load_results.fetch_finished_results("https://example.supabase.co", "key") == {
        25: {
            "phase": "group",
            "home_team": "mex",
            "away_team": "kor",
            "home_goals": 2,
            "away_goals": 1,
        },
        73: {
            "phase": "r32",
            "home_team": "zaf",
            "away_team": "can",
            "home_goals": 1,
            "away_goals": 1,
            "home_penalties": 4,
            "away_penalties": 5,
            "winner_team": "can",
        },
    }


def test_write_fixed_results_uses_compact_string_keys(tmp_path):
    path = tmp_path / "fixed_results.json"

    load_results.write_fixed_results(path, {
        25: {"phase": "group", "home_goals": 2, "away_goals": 1},
        3: (0, 0),
        73: {
            "phase": "r32",
            "home_team": "zaf",
            "away_team": "can",
            "home_goals": 1,
            "away_goals": 1,
            "home_penalties": 4,
            "away_penalties": 5,
            "winner_team": "can",
        },
    })

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["results"]["3"] == [0, 0]
    assert data["results"]["25"] == [2, 1]
    assert data["results"]["73"] == {
        "phase": "r32",
        "home_team": "zaf",
        "away_team": "can",
        "home_goals": 1,
        "away_goals": 1,
        "home_penalties": 4,
        "away_penalties": 5,
        "winner_team": "can",
    }
    assert data["fetched_at"].endswith("Z")
