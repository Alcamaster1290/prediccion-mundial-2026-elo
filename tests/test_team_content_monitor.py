import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_team_content_manifest_tracks_all_teams_and_asset_aliases():
    manifest = json.loads(read("data/team-content-manifest.json"))
    teams = manifest["teams"]

    assert manifest["meta"]["total_teams"] == 48
    assert len(teams) == 48
    assert {team["team_code"] for team in teams} >= {"jpn", "cuw", "mar", "pan"}

    by_code = {team["team_code"]: team for team in teams}
    assert by_code["jpn"]["asset_code"] == "jap"
    assert by_code["cuw"]["asset_code"] == "cur"
    assert by_code["jpn"]["assets"]["xi_image"] is True
    assert by_code["cuw"]["assets"]["star_image"] is True
    assert by_code["mar"]["assets"]["list_png"] is True
    assert by_code["mar"]["assets"]["list_txt"] is False
    assert "list_txt" in by_code["mar"]["local_missing"]

    missing_html = {
        team["team_code"]
        for team in teams
        if not team["local"]["html_section"]
    }
    assert missing_html == {"ksa", "jor"}


def test_grupos_modal_links_every_published_team_profile():
    manifest = json.loads(read("data/team-content-manifest.json"))
    html = read("index.html")

    expected_sections = {
        team["section_id"]
        for team in manifest["teams"]
        if team["local"]["html_section"]
    }
    modal_sections = set(re.findall(r'class="gmod-team has-analysis"[^>]+href="#([^"]+)"', html))
    inactive_codes = set(
        re.findall(r'<div class="gmod-team"[^>]*>\s*<img src="assets/flags/([a-z]{3})\.svg"', html)
    )

    assert modal_sections == expected_sections
    assert inactive_codes == {"ksa", "jor"}


def test_team_content_monitor_rpc_is_admin_only_and_reports_missing_fields():
    sql = read("supabase/21_admin_team_content_monitor.sql").lower()

    assert "create or replace function public.admin_get_team_data_status()" in sql
    assert "returns jsonb" in sql
    assert "security definer" in sql
    assert "set search_path = public, pg_temp" in sql
    assert "(select auth.uid())" in sql
    assert "public.has_staff_role('admin')" in sql
    assert "latest_run as" in sql
    assert "prediction_teams as" in sql
    assert "db_missing" in sql
    assert "player_rows" in sql
    assert "starter_rows" in sql
    assert "player_elo_rows" in sql
    assert "profile_published" in sql
    assert "simulation_rows" in sql
    assert "prediction_rows" in sql
    assert "revoke all on function public.admin_get_team_data_status() from public, anon" in sql
    assert "grant execute on function public.admin_get_team_data_status() to authenticated" in sql


def test_internal_admin_app_renders_team_content_monitor_without_table_reads():
    html = read("admin/premium-codes.html")
    js = read("js/admin-premium-codes.js")

    assert 'id="admin-team-content-status"' in html
    assert 'id="admin-team-summary"' in html
    assert 'id="admin-team-group-filter"' in html
    assert 'id="admin-team-missing-filter"' in html
    assert 'id="admin-team-search"' in html
    assert 'id="admin-team-status-rows"' in html
    assert "admin_get_team_data_status" in js
    assert "data/team-content-manifest.json" in js
    assert "loadTeamContentStatus" in js
    assert "mergeTeamContentStatus" in js
    assert "renderTeamContentRows" in js
    assert "local_missing" in js
    assert "db_missing" in js
    assert ".from(" not in js
