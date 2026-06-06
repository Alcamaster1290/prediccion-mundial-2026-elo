import pytest

from scripts.mark_xi_starters import apply_starters


def test_apply_starters_marks_only_configured_players():
    teams_data = {
        "teams": [
            {
                "id": "abc",
                "players": [
                    {"name": f"Player {number}", "titular": number == 12}
                    for number in range(1, 13)
                ],
            }
        ]
    }
    starters = {"abc": [f"Player {number}" for number in range(1, 12)]}

    report = apply_starters(teams_data, starters)

    assert report == {"abc": 11}
    players = teams_data["teams"][0]["players"]
    assert [player["titular"] for player in players] == [True] * 11 + [False]


def test_apply_starters_rejects_names_not_found_in_team():
    teams_data = {
        "teams": [
            {
                "id": "abc",
                "players": [{"name": f"Player {number}"} for number in range(1, 11)],
            }
        ]
    }
    starters = [f"Player {number}" for number in range(1, 11)] + ["Missing Player"]

    with pytest.raises(ValueError, match="abc missing starters"):
        apply_starters(teams_data, {"abc": starters})
