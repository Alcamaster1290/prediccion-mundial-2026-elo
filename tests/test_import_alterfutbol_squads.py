import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.import_alterfutbol_squads import (  # noqa: E402
    club_elo_map,
    load_club_elo_sources,
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
    complete_players[0]["elo"] = 1000
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


def test_club_elo_lookup_keeps_highest_elo_when_normalized_names_collide():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "FC Barcelona", "elo": 2019},
                {"club": "Barcelona SC", "elo": 1207},
                {"club": "Glasgow Rangers", "elo": 1468},
                {"club": "Rangers FC", "elo": 909},
            ]
        }
    )

    assert lookup_club_elo("Barcelona", club_elos) == 2019
    assert lookup_club_elo("Rangers FC", club_elos) == 1468


def test_club_elo_lookup_resolves_current_worldclubratings_names():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "OGC Nizza", "elo": 1384},
                {"club": "Los Angeles FC", "elo": 1384},
                {"club": "Atletico-MG", "elo": 1355},
                {"club": "Brighton &amp; Hove Albion", "elo": 1680},
                {"club": "Young Boys Bern", "elo": 1390},
                {"club": "FSV Mainz 05", "elo": 1568},
                {"club": "Borussia Mönchengladbach", "elo": 1583},
            ]
        }
    )

    assert lookup_club_elo("OGC Nice", club_elos) == 1384
    assert lookup_club_elo("LAFC", club_elos) == 1384
    assert lookup_club_elo("Atlético Mineiro", club_elos) == 1355
    assert lookup_club_elo("Brighton", club_elos) == 1680
    assert lookup_club_elo("BSC Young Boys", club_elos) == 1390
    assert lookup_club_elo("Mainz 05", club_elos) == 1568
    assert lookup_club_elo("B. Mönchengladbach", club_elos) == 1583


def test_club_elo_lookup_normalizes_source_suffixes_and_transliterations():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "Esteghlal F.C.", "elo": 1303},
                {"club": "Brøndby IF", "elo": 1383},
                {"club": "Jagiellonia Białystok", "elo": 1404},
                {"club": "Kasımpaşa Istanbul", "elo": 1237},
                {"club": "PFK Turan Tovuz", "elo": 1139},
            ]
        }
    )

    assert lookup_club_elo("Esteghlal FC", club_elos) == 1303
    assert lookup_club_elo("Brondby", club_elos) == 1383
    assert lookup_club_elo("Jagiellonia", club_elos) == 1404
    assert lookup_club_elo("Kasimpasa SK", club_elos) == 1237
    assert lookup_club_elo("FC Turan-Tovuz", club_elos) == 1139


def test_club_elo_lookup_resolves_source_backed_missing_squad_aliases():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "Al-Wakra", "elo": 1046},
                {"club": "UNAM Pumas", "elo": 1284},
                {"club": "VV St. Truiden", "elo": 1401},
                {"club": "Al Sharjah", "elo": 1239},
                {"club": "SC Freiburg", "elo": 1636},
                {"club": "Botafogo RJ", "elo": 1428},
                {"club": "Espanyol Barcelona", "elo": 1485},
                {"club": "FCSB Bukarest", "elo": 1409},
                {"club": "Zhejiang Professional", "elo": 1192},
            ]
        }
    )

    assert lookup_club_elo("Al-Wakrah SC", club_elos) == 1046
    assert lookup_club_elo("Pumas UNAM", club_elos) == 1284
    assert lookup_club_elo("Sint-Truidense VV", club_elos) == 1401
    assert lookup_club_elo("Sharjah FC", club_elos) == 1239
    assert lookup_club_elo("SC Friburgo", club_elos) == 1636
    assert lookup_club_elo("Botafogo", club_elos) == 1428
    assert lookup_club_elo("RCD Espanyol", club_elos) == 1485
    assert lookup_club_elo("FCSB", club_elos) == 1409
    assert lookup_club_elo("Zhejiang FC", club_elos) == 1192


def test_load_club_elo_sources_merges_supplement_files(tmp_path):
    primary = tmp_path / "primary.json"
    supplement = tmp_path / "supplement.json"
    primary.write_text(
        '{"meta":{"source":"primary"},"clubs":[{"club":"PSG","elo":2072}]}',
        encoding="utf-8",
    )
    supplement.write_text(
        '{"meta":{"source":"supplement"},"clubs":[{"club":"Norwich","elo":1538}]}',
        encoding="utf-8",
    )

    data = load_club_elo_sources(primary, [supplement])

    assert data["clubs"] == [
        {"club": "PSG", "elo": 2072},
        {"club": "Norwich", "elo": 1538},
    ]


def test_club_elo_lookup_resolves_flerosport_supplement_aliases():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "Norwich", "elo": 1538},
                {"club": "Waalwijk", "elo": 1324},
                {"club": "Düsseldorf", "elo": 1477},
                {"club": "Peterboro", "elo": 1380},
                {"club": "Santander", "elo": 1619},
                {"club": "FC AGMK", "elo": 1281},
                {"club": "Nancy", "elo": 1415},
                {"club": "Rotherham", "elo": 1328},
                {"club": "Luton", "elo": 1489},
                {"club": "Frosinone", "elo": 1588},
                {"club": "Dender", "elo": 1363},
            ]
        }
    )

    assert lookup_club_elo("Norwich City", club_elos) == 1538
    assert lookup_club_elo("RKC Waalwijk", club_elos) == 1324
    assert lookup_club_elo("Fortuna Düsseldorf", club_elos) == 1477
    assert lookup_club_elo("Peterborough United", club_elos) == 1380
    assert lookup_club_elo("Racing Santander", club_elos) == 1619
    assert lookup_club_elo("AGMK Olmaliq", club_elos) == 1281
    assert lookup_club_elo("AS Nancy Lorraine", club_elos) == 1415
    assert lookup_club_elo("Rotherham United", club_elos) == 1328
    assert lookup_club_elo("Luton Town", club_elos) == 1489
    assert lookup_club_elo("Frosinone Calcio", club_elos) == 1588
    assert lookup_club_elo("FCV Dender EH", club_elos) == 1363


def test_club_elo_lookup_resolves_elofootball_supplement_aliases():
    club_elos = club_elo_map(
        {
            "clubs": [
                {"club": "Igdir FK", "elo": 1478},
            ]
        }
    )

    assert lookup_club_elo("Igdir FK", club_elos) == 1478
    assert lookup_club_elo("Idgir FK", club_elos) == 1478
