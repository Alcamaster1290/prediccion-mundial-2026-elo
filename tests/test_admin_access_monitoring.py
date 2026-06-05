from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_admin_access_migration_extends_read_policies_and_monitoring_rpc():
    sql = read("supabase/18_admin_access_monitoring.sql").lower()

    assert "create or replace function public.admin_get_content_status()" in sql
    assert "security definer" in sql
    assert "set search_path = public, pg_temp" in sql
    assert "(select auth.uid())" in sql
    assert "public.has_staff_role('admin')" in sql
    assert "grant execute on function public.admin_get_content_status() to authenticated" in sql
    assert "revoke all on function public.admin_get_content_status() from public, anon" in sql

    for table_name in [
        "public.predictions",
        "public.team_strength_snapshots",
        "public.simulation_runs",
        "public.simulation_group_standings",
        "public.simulation_terceros_table",
        "public.players",
    ]:
        assert f"on {table_name} for select" in sql

    assert "match_results" in sql
    assert "simulation_group_standings" in sql
    assert "simulation_terceros_table" in sql
    assert "published_predictions" in sql
    assert "real_results" in sql


def test_staff_role_lookup_fix_avoids_current_role_identifier_collision():
    sql = read("supabase/19_fix_staff_role_lookup.sql").lower()

    assert "create or replace function public.has_staff_role" in sql
    assert "security definer" in sql
    assert "(select auth.uid())" in sql
    assert "staff_role text" in sql
    assert "current_role text" not in sql
    assert "grant execute on function public.has_staff_role(text) to authenticated" in sql
    assert "revoke all on function public.has_staff_role(text) from public, anon" in sql


def test_auth_treats_admin_role_as_full_access_without_profile_flag():
    auth_js = read("js/auth.js")

    assert "async function hasAdminRole()" in auth_js
    assert ".rpc('has_staff_role', { required_role: 'admin' })" in auth_js
    assert "var hasFullAccess = !!isPrem || !!isAdmin;" in auth_js
    assert "isAdmin: !!isAdmin" in auth_js
    assert "hasFullAccess: hasFullAccess" in auth_js
    assert "updateNavAuthUI(user, hasFullAccess)" in auth_js
    assert "PremiumSection.onAuthChange(user, hasFullAccess" in auth_js
    assert "PredicionesSection.onAuthChange(user, hasFullAccess" in auth_js
    assert "BracketSection.setPremiumState(hasFullAccess)" in auth_js


def test_internal_admin_app_monitors_simulation_and_real_result_loads():
    html = read("admin/premium-codes.html")
    js = read("js/admin-premium-codes.js")

    assert 'id="admin-content-status"' in html
    assert 'id="admin-simulation-status"' in html
    assert 'id="admin-real-results-status"' in html
    assert "admin_get_content_status" in js
    assert "loadContentStatus" in js
    assert "renderContentStatus" in js
    assert "simulation_group_standings" not in js
    assert "match_results" not in js
    assert ".from(" not in js
