import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import export_to_supabase  # noqa: E402
from generate_seed_sql import gen_mc  # noqa: E402


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
