import sys
import re
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import export_to_supabase  # noqa: E402
from generate_seed_sql import gen_mc, gen_players  # noqa: E402


def sample_mc_data():
    return {
        "runs": 10,
        "seed": 42,
        "teams": {
            "mex": {
                "qualified_pct": 90.0,
                "first_pct": 50.0,
                "second_pct": 30.0,
                "third_pct": 15.0,
                "best_third_pct": 10.0,
                "fourth_pct": 5.0,
                "points_pct": {"0": 0.0, "1": 5.0, "3": 20.0},
            }
        },
        "terceros_table": [
            {
                "rank": 1,
                "group": "A",
                "team_code": "mex",
                "third_pct": 15.0,
                "qualifies_pct": 10.0,
                "avg_pts": 3.2,
                "avg_gd": -0.4,
                "avg_gf": 2.1,
                "qualifies": True,
            }
        ],
    }


def test_gen_mc_includes_terceros_seed_rows(tmp_path):
    out_path = tmp_path / "seed_mc.sql"

    gen_mc(sample_mc_data(), out_path)

    sql = out_path.read_text(encoding="utf-8")
    assert "TRUNCATE simulation_terceros_table RESTART IDENTITY CASCADE;" in sql
    assert "INSERT INTO simulation_terceros_table" in sql
    assert "(simulation_run,rank,group_id,team_code,third_pct,qualifies_pct,avg_pts,avg_gd,avg_gf,qualifies)" in sql
    assert "(1,'A','mex',15.0,10.0,3.2,-0.4,2.1,TRUE)" in sql


def test_gen_players_includes_club_country_seed_column(tmp_path):
    out_path = tmp_path / "seed_players.sql"
    teams_data = {
        "teams": [
            {
                "id": "mex",
                "players": [
                    {
                        "number": 9,
                        "pos": "FW",
                        "name": "Raúl Jiménez",
                        "age": 35,
                        "club": "Fulham FC",
                        "country": "Inglaterra",
                        "elo": None,
                        "titular": True,
                    }
                ],
            }
        ]
    }

    gen_players(teams_data, out_path)

    sql = out_path.read_text(encoding="utf-8")
    assert "(team_code,shirt_number,pos,name,age,club,club_country,elo_club,elo_player,titular,version)" in sql
    assert "('mex',9,'FW','Raúl Jiménez',35,'Fulham FC','Inglaterra',NULL,NULL,TRUE,'1.0')" in sql


def test_build_player_rows_includes_club_country():
    rows = export_to_supabase.build_player_rows(
        {
            "teams": [
                {
                    "id": "mex",
                    "players": [
                        {
                            "number": 9,
                            "pos": "FW",
                            "name": "Raúl Jiménez",
                            "age": 35,
                            "club": "Fulham FC",
                            "country": "Inglaterra",
                            "elo": None,
                            "titular": True,
                        }
                    ],
                }
            ]
        }
    )

    assert rows[0]["club_country"] == "Inglaterra"


def test_complete_squad_only_team_profiles_are_published_without_dt_source():
    public_rows, premium_rows = export_to_supabase.build_team_profile_rows(
        {
            "teams": [
                {
                    "id": "mex",
                    "source_status": "squad_only",
                    "scheme": "4-3-3",
                    "xi_image": "assets/xi/mex-xi.png",
                    "dt": "Javier Aguirre",
                    "dt_source": "xi_image",
                    "tactics": ["Bloque compacto", "Salida vertical"],
                    "players": [
                        {"name": f"Player {index}", "titular": index <= 11}
                        for index in range(1, 27)
                    ],
                }
            ]
        }
    )

    assert public_rows[0]["published"] is True
    assert "dt_source" not in public_rows[0]
    assert "dt_source" not in premium_rows[0]


def test_incomplete_squad_only_team_profiles_stay_unpublished():
    public_rows, _ = export_to_supabase.build_team_profile_rows(
        {
            "teams": [
                {
                    "id": "ksa",
                    "source_status": "squad_only",
                    "scheme": None,
                    "xi_image": None,
                    "tactics": [],
                    "players": [],
                }
            ]
        }
    )

    assert public_rows[0]["published"] is False


def test_players_schema_includes_club_country_column():
    schema = (Path(__file__).resolve().parents[1] / "supabase" / "05_prediction_engine_schema.sql").read_text(
        encoding="utf-8"
    )

    assert "club_country TEXT" in schema
    assert "ADD COLUMN IF NOT EXISTS club_country TEXT" in schema


def test_predictions_match_id_has_regular_unique_index_for_postgrest_upsert():
    repo = Path(__file__).resolve().parents[1]
    schema = (repo / "supabase" / "01_schema.sql").read_text(encoding="utf-8")
    migration = (repo / "supabase" / "23_predictions_match_id_unique.sql").read_text(encoding="utf-8")

    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_match_id_unique ON public.predictions(match_id);" in schema
    assert "DROP INDEX IF EXISTS public.idx_predictions_match_id_unique;" in migration
    assert "CREATE UNIQUE INDEX idx_predictions_match_id_unique" in migration
    assert "ON public.predictions(match_id)" in migration
    index_defs = re.findall(
        r"CREATE UNIQUE INDEX(?: IF NOT EXISTS)? idx_predictions_match_id_unique\s+ON public\.predictions\(match_id\)[^;]*;",
        schema + migration,
        flags=re.S,
    )
    assert index_defs
    assert all("WHERE" not in index_def.upper() for index_def in index_defs)
    assert "NOTIFY pgrst, 'reload schema';" in migration


def test_export_mc_results_uploads_terceros_table(monkeypatch):
    calls = []

    def fake_request(url, key, method, path, body=None, prefer="resolution=merge-duplicates,return=minimal"):
        calls.append({"method": method, "path": path, "body": body, "prefer": prefer})
        if path == "simulation_runs":
            return None, [{"id": "run-123"}]
        return None, None

    monkeypatch.setattr(export_to_supabase, "supabase_request", fake_request)

    ok = export_to_supabase.export_mc_results(
        "https://example.supabase.co",
        "service-role-key",
        sample_mc_data(),
        version="1.1",
    )

    assert ok is True
    terceros_call = next(call for call in calls if call["path"] == "simulation_terceros_table")
    assert terceros_call["body"] == [
        {
            "simulation_run": "run-123",
            "rank": 1,
            "group_id": "A",
            "team_code": "mex",
            "third_pct": 15.0,
            "qualifies_pct": 10.0,
            "avg_pts": 3.2,
            "avg_gd": -0.4,
            "avg_gf": 2.1,
            "qualifies": True,
        }
    ]
