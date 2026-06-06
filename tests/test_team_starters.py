import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_every_loaded_team_has_exactly_eleven_starters():
    teams = json.loads((REPO_ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]

    missing = []
    for team in teams:
        players = team.get("players") or []
        if not players:
            continue
        starter_count = sum(1 for player in players if player.get("titular") is True)
        if starter_count != 11:
            missing.append(f"{team['id']}:{starter_count}")

    assert missing == []
