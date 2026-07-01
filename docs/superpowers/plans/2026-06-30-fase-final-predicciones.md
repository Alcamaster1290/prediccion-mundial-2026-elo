# Fase Final Predictions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar predicciones de eliminatorias, abrir la seccion de predicciones a usuarios gratis y corregir la resolucion Supabase de mejores terceros.

**Architecture:** Keep group-stage predictions in the existing `predictions` table and generate knockout predictions into a public JSON asset consumed by `predicciones.js`. Use public Supabase RPCs for final group standings and best thirds for anon/free users, while preserving premium table RLS. Fix the canonical knockout RPC by resolving third-place slot labels from `v_best_thirds` with the same assignment search used by the frontend.

**Tech Stack:** Python data generation, vanilla JS frontend, Supabase Postgres migrations/RPC, pytest and Node syntax checks.

---

### Task 1: Data Contract For Knockout Predictions

**Files:**
- Create: `scripts/generate_final_phase_predictions.py`
- Create: `data/final_phase_predictions.json`
- Test: `tests/test_final_phase_predictions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_final_phase_predictions_resolve_full_projected_bracket():
    data = load_final_phase_predictions()
    matches = data["matches"]
    assert len(matches) == 32
    assert [m["match_number"] for m in matches[:16]] == list(range(73, 89))
    assert all(m["home_team"] and m["away_team"] for m in matches)
    assert all(len(m["top_scorelines"]) == 10 for m in matches)
    assert all(round(m["advance_home_pct"] + m["advance_away_pct"], 1) == 100.0 for m in matches)
```

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_final_phase_predictions.py -q`
Expected: fail because the test file or generated JSON does not exist.

- [ ] **Step 3: Implement generator**

Create `scripts/generate_final_phase_predictions.py` that reads `data/fixed_results.json`, `data/matches.json`, `data/groups.json`, `data/knockout_matches.json`, `data/team_strength_snapshots.json`, `data/model_weights.json`, and `data/teams.json`; resolves R32; projects winners by advance probability; writes `data/final_phase_predictions.json`.

- [ ] **Step 4: Verify green**

Run: `python scripts/generate_final_phase_predictions.py` then `pytest tests/test_final_phase_predictions.py -q`.

### Task 2: Public Prediction UI

**Files:**
- Modify: `js/supa-data.js`
- Modify: `js/predicciones.js`
- Modify: `js/premium.js`
- Modify: `index.html`
- Test: `tests/test_pronosticos_embedded_order.py`
- Test: `tests/test_public_predictions_ui.py`

- [ ] **Step 1: Write failing UI source tests**

```python
def test_predictions_page_has_group_and_final_phase_tabs():
    js = read("js/predicciones.js")
    assert "pred-phase-tab" in js
    assert "Fase Final" in js
    assert "loadFinalPhasePredictions" in js
    assert "renderFinalPhasePredictions" in js
```

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_public_predictions_ui.py tests/test_pronosticos_embedded_order.py -q`
Expected: fail because phase tabs and final phase rendering do not exist.

- [ ] **Step 3: Implement UI**

Add public data fallback in `SupaData.loadSimulationData()`, render `Predicciones` for anon/free users, add phase tabs, make group pronosticos collapsible, and render final-phase cards with team anchors.

- [ ] **Step 4: Verify green**

Run: `node --check js/supa-data.js`, `node --check js/predicciones.js`, `node --check js/premium.js`, and the UI tests.

### Task 3: Supabase Knockout Best Thirds Fix

**Files:**
- Create: `supabase/30_resolve_knockout_best_thirds.sql`
- Test: `tests/test_supabase_automation_plan.py`

- [ ] **Step 1: Write failing migration test**

```python
def test_knockout_rpc_resolves_best_third_labels():
    sql = read("supabase/30_resolve_knockout_best_thirds.sql").lower()
    assert "create or replace function public.resolve_knockout_bracket()" in sql
    assert "best_third_slots" in sql
    assert "regexp_match" in sql
    assert "grant execute on function public.resolve_knockout_bracket()" in sql
```

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_supabase_automation_plan.py::test_knockout_rpc_resolves_best_third_labels -q`
Expected: fail because migration is missing.

- [ ] **Step 3: Implement migration and apply remotely**

Create SQL that keeps direct group-rank resolution and resolves `manual_label` third-place slots by parsing labels and assigning classified third-place teams once each.

- [ ] **Step 4: Verify green and remote**

Run the migration SQL against Supabase, then call `resolve_knockout_bracket()` as anon and assert R32 has no `NULL` teams.

### Task 4: Full Verification

**Files:**
- Modify only files touched above.

- [ ] **Step 1: Run data validation**

Run: `python scripts/validate_data.py`
Expected: PASS.

- [ ] **Step 2: Run focused tests**

Run: `pytest tests/test_final_phase_predictions.py tests/test_public_predictions_ui.py tests/test_pronosticos_embedded_order.py tests/test_supabase_automation_plan.py tests/test_bracket_best_thirds.py`
Expected: PASS.

- [ ] **Step 3: Verify Supabase visibility**

Use anon key to verify 72 `predictions`, 48 `get_group_standings`, 12 `get_best_thirds`, 12 `get_bracket_projection.groups`, and 16 resolved R32 matches.

- [ ] **Step 4: Inspect diff**

Run: `git diff --stat` and review changed files before reporting.
