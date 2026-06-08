from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8").lower()


def test_prediction_engine_schema_matches_exported_simulation_run_columns():
    schema = read("supabase/05_prediction_engine_schema.sql")

    for column in ["scenario_name", "model_version", "is_active", "completed_at", "input_hash"]:
        assert column in schema
    assert "idx_simulation_runs_one_active_scenario" in schema
    assert "idx_players_team_name_club_version" in schema


def test_prediction_engine_rls_hardens_all_premium_tables():
    sql = read("supabase/07_prediction_engine_rls_hardening.sql")
    premium_tables = [
        "team_strength_snapshots",
        "simulation_runs",
        "simulation_group_standings",
        "simulation_terceros_table",
        "players",
    ]

    assert "revoke all on table" in sql
    assert "from public, anon" in sql
    assert "revoke insert, update, delete on table" in sql
    assert "from authenticated" in sql
    assert "to service_role" in sql
    assert "p.is_premium = true" in sql
    for table in premium_tables:
        assert table in sql


def test_security_advisors_hardening_is_idempotent_for_optional_functions():
    sql = read("supabase/08_security_advisors_hardening.sql")

    assert "to_regprocedure('public.rls_auto_enable()')" in sql
    assert "to_regprocedure('public.set_updated_at()')" in sql
    assert "redeem_premium_code(text)" in sql
