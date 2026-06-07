from scripts.import_alterfutbol_squads import (
    club_elo_map,
    lookup_club_elo,
    merge_squad_only_teams,
)


def test_merge_squad_only_teams_adds_only_complete_missing_sources():
    complete_players = [
        {
            "number": None,
            "pos": "GK",
            "name": f"Jugador {index}",
            "age": 20 + index % 10,
            "club": "PSG" if index == 1 else f"Club {index}",
            "country": None,
            "elo": None,
            "titular": False,
        }
        for index in range(1, 27)
    ]
    teams_data = {
        "meta": {"updated": "2026-06-02", "total_teams_analyzed": 1},
        "teams": [{"id": "kor", "name": "Corea del Sur", "group": "A", "analyzed": True, "players": []}],
    }
    source_manifest = {
        "teams": [
            {
                "team_code": "mex",
                "name": "México",
                "group_id": "A",
                "url": "https://example.test/mexico/",
                "title": "México anunció sus convocados",
                "published_date": "2026-06-03",
                "status": "complete",
                "players": complete_players,
            },
            {
                "team_code": "jor",
                "name": "Jordania",
                "group_id": "J",
                "url": None,
                "status": "missing_article",
                "players": [],
            },
        ]
    }
    groups_data = {"groups": [{"id": "A", "teams": ["mex", "kor"]}, {"id": "J", "teams": ["jor"]}]}
    club_elos = {"PSG": 2038}

    merged, added = merge_squad_only_teams(teams_data, source_manifest, groups_data, club_elos)

    by_code = {team["id"]: team for team in merged["teams"]}
    assert added == ["mex"]
    assert set(by_code) == {"kor", "mex"}
    assert by_code["kor"]["analyzed"] is True
    assert by_code["mex"]["analyzed"] is False
    assert by_code["mex"]["source_url"] == "https://example.test/mexico/"
    assert by_code["mex"]["source_status"] == "squad_only"
    assert by_code["mex"]["players"][0]["elo"] == 2038
    assert all(player["titular"] is False for player in by_code["mex"]["players"])
    assert merged["meta"]["total_teams_analyzed"] == 1
    assert merged["meta"]["total_teams_with_squads"] == 2


def test_club_elo_lookup_resolves_common_source_aliases():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "AC Mailand", "elo": 1688},
                {"club": "FC Arsenal", "elo": 2106},
                {"club": "Inter Mailand", "elo": 1864},
                {"club": "Olympique Marseille", "elo": 1588},
                {"club": "FC Kopenhagen", "elo": 1495},
            ]
        }
    )

    assert lookup_club_elo("AC Milan", club_elos) == 1688
    assert lookup_club_elo("Milan", club_elos) == 1688
    assert lookup_club_elo("Arsenal", club_elos) == 2106
    assert lookup_club_elo("Inter de Milán", club_elos) == 1864
    assert lookup_club_elo("Olympique de Marsella", club_elos) == 1588
    assert lookup_club_elo("FC Copenhague", club_elos) == 1495
