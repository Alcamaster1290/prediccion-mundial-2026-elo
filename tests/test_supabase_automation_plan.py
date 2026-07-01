import importlib
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_tournament_core_migration_defines_match_results_and_realtime():
    sql = read("supabase/09_tournament_core.sql").lower()

    assert "create table if not exists public.match_results" in sql
    assert re.search(r"match_number\s+integer\s+primary key", sql)
    assert re.search(r"home_goals\s+integer", sql)
    assert re.search(r"away_goals\s+integer", sql)
    assert "alter table public.match_results enable row level security" in sql
    assert "grant select on table" in sql and "match_results" in sql
    assert "supabase_realtime" in sql


def test_security_migration_removes_direct_premium_profile_updates():
    sql = read("supabase/13_staff_roles.sql").lower()

    assert 'drop policy if exists "profiles: self update"' in sql
    assert "create policy" in sql
    assert "profiles: self update safe fields" in sql
    assert "revoke update on table public.profiles" in sql
    assert "grant update (email, full_name, updated_at) on table public.profiles" in sql
    assert "create schema if not exists app_private" in sql
    assert "create table if not exists app_private.staff_roles" in sql
    assert "create or replace function public.has_staff_role" in sql
    assert "security definer" in sql


def test_views_use_security_invoker_and_expose_standings_rpc():
    sql = read("supabase/10_standings_views.sql").lower()

    assert "with (security_invoker = true)" in sql
    assert "create or replace view public.v_group_standings" in sql
    assert "create or replace view public.v_best_thirds" in sql
    assert "create or replace function public.get_group_standings" in sql
    assert "grant execute on function public.get_group_standings" in sql


def test_knockout_profiles_snapshots_and_premium_ops_migrations_exist():
    ko_sql = read("supabase/11_knockout_rules.sql").lower()
    profiles_sql = read("supabase/12_team_profiles.sql").lower()
    snapshots_sql = read("supabase/14_simulation_snapshots.sql").lower()
    premium_sql = read("supabase/15_premium_ops.sql").lower()
    advisor_sql = read("supabase/16_advisor_hardening.sql").lower()

    assert "create table if not exists public.knockout_slot_rules" in ko_sql
    assert "create or replace function public.resolve_knockout_bracket" in ko_sql
    assert "create table if not exists public.team_profiles" in profiles_sql
    assert "create or replace view public.v_public_team_profiles" in profiles_sql
    assert "alter table public.simulation_runs" in snapshots_sql
    assert "scenario_name text not null default 'baseline'" in snapshots_sql
    assert "create or replace function public.get_active_simulation_snapshot" in snapshots_sql
    assert "create table if not exists public.premium_grants" in premium_sql
    assert "create table if not exists public.premium_audit_log" in premium_sql
    assert "create or replace function public.grant_premium" in premium_sql
    assert "create or replace function public.revoke_premium" in premium_sql
    assert "alter function public.resolve_knockout_bracket() set search_path" in advisor_sql
    assert "alter column scenario_name set default 'baseline'" in advisor_sql
    assert "idx_knockout_slot_rules_source_group" in advisor_sql
    assert 'drop policy if exists "premium grants: admin all"' in advisor_sql
    assert "staff roles: service role all" in advisor_sql


def test_export_to_supabase_builds_match_prediction_and_pipeline_rows():
    export_to_supabase = importlib.import_module("export_to_supabase")
    export_sql = read("scripts/export_to_supabase.py")

    groups = {
        "groups": [
            {
                "id": "A",
                "teams": ["mex", "zaf", "kor", "cze"],
                "fixtures": [
                    {
                        "date": "2026-06-11",
                        "time": "19:00",
                        "home": "mex",
                        "away": "zaf",
                        "venue": "Estadio Azteca, Ciudad de Mexico",
                    }
                ],
            }
        ]
    }
    knockout = [
        {
            "phase": "r32",
            "matchNum": 73,
            "date": "2026-06-28",
            "time": "19:00",
            "homeLabel": "2. Grupo A",
            "awayLabel": "2. Grupo B",
            "venue": "SoFi Stadium",
            "city": "Los Angeles",
        }
    ]
    rows = export_to_supabase.build_match_rows(groups, knockout)

    assert [row["match_number"] for row in rows] == [1, 73]
    assert rows[0]["phase"] == "group"
    assert rows[0]["group_id"] == "A"
    assert rows[0]["status"] == "scheduled"
    assert rows[1]["phase"] == "r32"
    assert rows[1]["home_label"] == "2. Grupo A"
    assert "mc_data.get('scenario_name', 'baseline')" in export_sql


def test_frontend_loads_supa_data_before_feature_modules():
    html = read("index.html")
    scripts = re.findall(r'<script src="([^"]+)"></script>', html)

    assert "js/supa-data.js" in scripts
    assert scripts.index("js/supa-data.js") < scripts.index("js/auth.js")
    assert scripts.index("js/supa-data.js") < scripts.index("js/standings.js")

    supa_data = read("js/supa-data.js")
    assert "window.SupaData" in supa_data
    assert "loadSupabaseOrLocal" in supa_data
    assert "isLocalDev" in supa_data
    assert "if (!localUrl || !isLocalDev()) return null;" in supa_data
    assert "redeemPremiumCode" in supa_data
    assert "getSession(client)" in supa_data
    assert ".eq('is_active', true)" in supa_data


def test_bracket_does_not_load_premium_data_before_access():
    bracket_js = read("js/bracket.js")

    init_body = re.search(r"function init\(\) \{(.*?)\n  \}", bracket_js, flags=re.S).group(1)
    assert "loadSimulationData()" not in init_body
    assert "if (hasPremiumAccess && !hasLoadedPremiumData) loadAndRenderPremiumData();" in bracket_js
    assert "el.innerHTML = renderBracket(null);" in bracket_js
    assert "window.__authState && window.__authState.hasFullAccess" in bracket_js


def test_knockout_rpc_resolves_best_third_labels():
    sql = read("supabase/30_resolve_knockout_best_thirds.sql").lower()

    assert "create or replace function public.resolve_knockout_slot_team" in sql
    assert "create or replace function public.resolve_knockout_bracket()" in sql
    assert "best_third_slots" in sql
    assert "regexp_match" in sql
    assert "match_winner" in sql
    assert "match_loser" in sql
    assert "source_match_number" in sql
    assert "winner_team" in sql
    assert "public.v_best_thirds" in sql
    assert "grant execute on function public.resolve_knockout_bracket()" in sql
