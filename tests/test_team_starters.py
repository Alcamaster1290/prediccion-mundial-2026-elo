import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.import_alterfutbol_squads import club_elo_map, lookup_club_elo  # noqa: E402


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


def test_every_loaded_player_has_club_country():
    teams = json.loads((REPO_ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]

    missing = []
    for team in teams:
        for player in team.get("players") or []:
            if not player.get("country"):
                missing.append(f"{team['id']}:{player['name']}:{player.get('club')}")

    assert missing == []


def test_every_loaded_team_has_coach_name():
    teams = json.loads((REPO_ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]

    missing = [
        team["id"]
        for team in teams
        if not (team.get("dt") or "").strip()
    ]

    assert missing == []


def test_squad_only_coaches_are_sourced_from_xi_images():
    teams = json.loads((REPO_ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]

    missing_source = [
        team["id"]
        for team in teams
        if team.get("source_status") == "squad_only"
        and team.get("dt_source") != "xi_image"
    ]

    assert missing_source == []


def test_every_resolvable_player_club_has_elo_assigned():
    teams = json.loads((REPO_ROOT / "data" / "teams.json").read_text(encoding="utf-8"))["teams"]
    club_elos = club_elo_map(json.loads((REPO_ROOT / "data" / "club_elo.json").read_text(encoding="utf-8")))

    missing = []
    santiago_elo = None
    for team in teams:
        for player in team.get("players") or []:
            if team["id"] == "mex" and player.get("name") == "Santiago Giménez":
                santiago_elo = player.get("elo")
            if player.get("elo") is not None:
                continue
            if lookup_club_elo(player.get("club"), club_elos) is not None:
                missing.append(f"{team['id']}:{player['name']}:{player.get('club')}")

    assert missing == []
    assert santiago_elo == 1688
