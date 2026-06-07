from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_elo_model_rpc_is_full_access_only_and_reports_team_coverage():
    migration = REPO_ROOT / "supabase/22_elo_model_explainer.sql"
    probability_migration = REPO_ROOT / "supabase/24_elo_probability_formula_explainer.sql"
    assert migration.exists()
    assert probability_migration.exists()

    sql = (migration.read_text(encoding="utf-8") + "\n" + probability_migration.read_text(encoding="utf-8")).lower()

    assert "create or replace function public.get_elo_model_explainer()" in sql
    assert "returns jsonb" in sql
    assert "security definer" in sql
    assert "set search_path = public, pg_temp" in sql
    assert "(select auth.uid())" in sql
    assert "p.is_premium = true" in sql
    assert "public.has_staff_role('admin')" in sql
    assert "club_adj_weight" in sql
    assert "avg_xi_blend" in sql
    assert "round(avg(elo_club_avg)" in sql
    assert "1675.3" not in sql
    assert "base_goals_per_team" in sql
    assert "probability_formula" in sql
    assert "elo expected-score" in sql
    assert "2 * base_goals_per_team" in sql
    assert "starter_elo_rows" in sql
    assert "coverage_tier" in sql
    assert "xi_blend_ready" in sql
    assert "needs_player_elo" in sql
    assert "elo_intl_only" in sql
    assert "revoke all on function public.get_elo_model_explainer() from public, anon" in sql
    assert "grant execute on function public.get_elo_model_explainer() to authenticated" in sql


def test_predictions_page_renders_elo_explainer_from_private_rpc():
    html = read("index.html")
    pred_js = read("js/predicciones.js")

    assert ".pred-elo-model" in html
    assert ".pred-elo-team-table" in html
    assert "loadEloModelExplainer" in pred_js
    assert "renderEloModelExplainer" in pred_js
    assert "get_elo_model_explainer" in pred_js
    assert "Modelo ELO" in pred_js
    assert "ELO internacional" in pred_js
    assert "XI titular" in pred_js
    assert "promedio XI actual" in pred_js
    assert "model.avg_xi_blend" in pred_js
    assert "model.probability_formula" in pred_js
    assert "model.base_goals_per_team" in pred_js
    assert "Probabilidad partido" in pred_js
    assert "Listo para XI" in pred_js
    assert "Base internacional" in pred_js
    assert "needs_player_elo" in pred_js
    assert "acceso completo" in pred_js
