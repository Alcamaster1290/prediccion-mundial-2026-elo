import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_predictions_page_has_group_and_final_phase_tabs():
    pred_js = read("js/predicciones.js")

    assert "pred-phase-tab" in pred_js
    assert "Fase Final" in pred_js
    assert "loadFinalPhasePredictions" in pred_js
    assert "renderFinalPhasePredictions" in pred_js
    assert "showPhaseTab" in pred_js
    assert 'id="pred-phase-final"' in pred_js


def test_group_pronosticos_are_rendered_inside_collapsible_block():
    premium_js = read("js/premium.js")

    assert "prono-group-disclosure" in premium_js
    assert "<details" in premium_js
    assert "Pronósticos Fase de Grupos" in premium_js


def test_predictions_section_renders_for_free_and_anon_users():
    pred_js = read("js/predicciones.js")
    match = re.search(
        r"async function onAuthChange\(user, isPremium, profile\) \{(.*?)\n  \}",
        pred_js,
        re.S,
    )
    assert match, "onAuthChange function missing"
    body = match.group(1)

    assert "await renderActive();" in body
    assert "renderLocked()" not in body
    assert "renderPaywall(profile)" not in body


def test_predictions_fallback_does_not_throw_without_supabase_cdn():
    auth_js = read("js/auth.js")
    pred_js = read("js/predicciones.js")

    assert "if (!window.supabase)" in auth_js
    assert "return null;" in auth_js

    match = re.search(
        r"async function loadEloModelExplainer\(\) \{(.*?)\n  \}",
        pred_js,
        re.S,
    )
    assert match, "loadEloModelExplainer function missing"
    body = match.group(1)

    assert "window.SupaData && window.SupaData.getClient" in body
    assert "window.SupaAuth && window.SupaAuth.getClient" not in body


def test_public_simulation_loader_uses_public_standings_when_no_session():
    supa_js = read("js/supa-data.js")

    assert "loadPublicSimulationData" in supa_js
    assert "get_group_standings" in supa_js
    assert "get_best_thirds" in supa_js
    assert "get_bracket_projection" in supa_js
