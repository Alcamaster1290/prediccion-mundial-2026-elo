# Prediction Engine - Technical Reference

## Overview

Python-based ELO simulation engine for the 2026 World Cup, covering both the
group stage and the knockout bracket. The pipeline builds team strengths from
public international ELO plus sourced club ELO for expected starters, applies a
small starter line-matchup adjustment per match, simulates group matches with
Poisson goal counts, projects the knockout rounds once groups conclude, and
exports premium outputs to Supabase.

Architecture principle: Python performs model computation, JavaScript displays
authorized data, and Supabase stores the public/premium boundary through grants
and RLS.

---

## Data Files

| File | Purpose |
|------|---------|
| `data/groups.json` | Source of truth: 12 groups and 72 official group fixtures. |
| `data/matches.json` | Generated flat list of 72 matches with unique `match_id`. |
| `data/match_context.json` | Legacy/context layer. Must provide `elo_intl` in team contexts; prediction text now prioritizes XI matchup notes. |
| `data/teams.json` | Squad data, starters, club, club country, club ELO and XI metadata. |
| `data/club_elo.json` | Club ELO reference data from worldclubratings.com. |
| `data/model_weights.json` | Current model configuration. |
| `data/team_strength_snapshots.json` | Generated team strength snapshot. Treat as premium-derived output when simulations are premium. |
| `data/mc_results.json` | Generated Monte Carlo output. Treat as premium-derived output when simulations are premium. |
| `data/predictions_seed.sql` | Generated match predictions for Supabase import. Treat as premium-derived output. |
| `data/knockout_matches.json` | Knockout fixture (16avos → Final, `matchNum` 73-104) with slot labels. |
| `data/fixed_results.json` | Real scores mirrored from the live `match_results` table (gitignored). |
| `data/final_phase_predictions.json` | Generated knockout projection (6 rounds: r32/r16/qf/sf/tp/final). |

Generated premium outputs are ignored by Git and should be regenerated locally
when needed, then exported to Supabase. Do not publish them as public static
assets in production.

---

## Model Weights

`data/model_weights.json` is the single source for model constants:

| Field | Current meaning |
|-------|-----------------|
| `_version` | Model/data version written to generated outputs. Current value: `1.3`. |
| `_note` | Human-readable summary of the model formula. |
| `club_adj_weight` | Weight applied to the starter XI club-ELO delta against the global XI average. |
| `xi_matchup_weight` | Weight applied per match to starter line matchup edges. |
| `base_goals_per_team` | Half of the fixed expected-goals total used by Poisson probabilities. Calibrated v1.3 value: `1.25`. |
| `elo_scale` | ELO logistic scale for win expectancy. Expected and preferred value is `400`. |
| `elo_lambda_scale` | Logistic scale used only for the goal-share split (v1.3). Current value: `800`. Equivalent to the legacy ratio divisor `2 * elo_lambda_scale = 1600`. |
| `draw_bias` | Maximum parity-aware draw boost applied to the 1X2 outcome (v1.3). Current value: `0.08`. |
| `parity_scale` | ELO gap at which the draw boost fades to zero (v1.3). Current value: `800`. |

The old fields `elo_intl_weight` and `xi_club_blend_weight` are obsolete. Model
weights do not sum to `1.0`; the current formula is an additive adjustment on
the international ELO scale.

Reserved for v1.4 (documented, not read by the engine yet):
`fecha1_caution_draw_boost` and `fecha3_context_draw_boost`, intended for
matchday-context draw adjustments. Matchday-3 logic requires simulating the
group state after two rounds, so it is intentionally out of scope for v1.3.

---

## Team Strength

`scripts/build_team_strength.py` writes `data/team_strength_snapshots.json`.

Current formula:

```text
score = elo_intl + (xi_blend - avg_xi_blend) * club_adj_weight
```

Where:

- `elo_intl` comes from `data/international_elo.json`.
- `xi_blend` is the average club ELO of titular players in `data/teams.json`.
- `avg_xi_blend` is the global average across teams with starter XI club ELO.
- `club_adj_weight` comes from `data/model_weights.json`.

Teams without a sourced XI remain `elo_intl_only`.

```bash
python scripts/build_team_strength.py
```

---

## Match Probability

`scripts/elo_probability.py` converts team strengths into outcome probabilities.
It uses the standard ELO expected-score curve and splits a fixed expected-goals
total, then applies a parity-aware draw correction (v1.3):

```text
share_a = 1 / (1 + 10 ^ (-(strength_a - strength_b) / elo_lambda_scale))
total_goals = 2 * base_goals_per_team
lambda_a = total_goals * share_a
lambda_b = total_goals * (1 - share_a)

# 1X2 from the joint Poisson score matrix, then:
parity = max(0, 1 - |strength_a - strength_b| / parity_scale)
boost = min(draw_bias * parity, 0.95 * (p_a + p_b))
p_draw' = p_draw + boost
p_a' = p_a - boost * p_a / (p_a + p_b)
p_b' = p_b - boost * p_b / (p_a + p_b)
```

`elo_lambda_scale` decouples the goal split from the win-expectancy
`elo_scale`; when absent it falls back to `elo_scale` (legacy behavior). The
legacy ratio divisor from old notes maps to `2 * elo_lambda_scale`.

`adjust_result_probabilities_for_draw` is a pure function: the output triple
always sums to 1, no probability goes negative (the boost is capped at 95% of
the decisive mass), the boost is maximal for even matches and zero once the
strength gap reaches `parity_scale`, and the added draw mass is taken from
`p_a` and `p_b` proportionally so favoritism direction is preserved.

The simulator (`scripts/simulate_group_stage.py`) applies the same correction
when sampling scorelines: it reweights the win/draw/loss classes of the joint
truncated Poisson score matrix to match the adjusted 1X2 probabilities,
preserving relative scoreline likelihoods within each class. The per-match
matrix is cached (`match_score_sampler`, `lru_cache`), so Monte Carlo cost
stays close to the legacy direct-Poisson path. With `draw_bias = 0` the
simulator uses the legacy untruncated Poisson sampling unchanged.

---

## Starter XI Matchup Layer

`scripts/xi_matchups.py` builds starter line profiles from `data/teams.json` and
compares:

- attack vs opponent defense
- midfield vs opponent midfield
- defense vs opponent attack
- goalkeeper vs opponent attack

`scripts/generate_predictions.py`, `scripts/simulate_group_stage.py`, and
`scripts/run_monte_carlo.py` use `xi_matchup_weight` to make a small
match-specific strength adjustment. This means two teams with similar aggregate
`xi_blend` can still produce different effective strengths depending on how
their starter lines match up.

---

## Calibration (v1.3)

### Problem detected

The v1.2 engine produced a points distribution hyperconcentrated on 0, 3, 6
and 9 points. Measured with `scripts/calibration_report.py` (10,000 runs,
seed 42) before calibration:

| Metric | v1.2 value | Target range |
|--------|-----------|--------------|
| Draw rate | 15.3% | 24% – 31% |
| Goals per match | 2.60 | 2.3 – 2.8 |
| 0-0 rate | 7.4% | 5% – 10% |
| 1-1 rate | 5.9% | 8% – 14% |
| Blowouts (3+ goal margin) | 31.8% | ≤ 18% (review above) |
| Points mass on 1,2,4,5,7 | 38.8% (2 pts: 3.0%, 5 pts: 3.0%) | visible mass on all |

Root cause: the goal share used the win-expectancy curve with `elo_scale =
400` directly, so a 200-point ELO gap already produced a 76/24 goal split and
a 400-point gap a 91/9 split. That crushed the draw rate in any non-even match
and inflated blowouts, which is exactly what concentrates final points on
9/6/3/0.

### Targets

World Cup-like group-stage ranges (not strict historical fitting):
`draw_rate` 24–31%, `goals_per_match` 2.3–2.8, `zero_zero_rate` 5–10%,
`one_one_rate` 8–14%, `blowout_3plus_rate` flagged above 18%, and the points
distribution must show visible mass on 1, 2, 4, 5 and 7 points. Encoded in
`TARGETS` inside `scripts/calibration_report.py`.

### Parameter search and chosen values

Grid search (`--grid`): `base_goals_per_team` × `elo_lambda_scale` ×
`draw_bias`, scored analytically against the targets (squared normalized
distance outside each range plus a favoritism guard), with a Monte Carlo
points-distribution check for the finalists. The user-suggested divisor range
800–1200 (`elo_lambda_scale` 400–600) could not push blowouts below ~20%
because the strength spread after the XI adjustment reaches ~800 ELO points,
so the search was extended to `elo_lambda_scale = 700/800` and
`parity_scale = 800`. Chosen combination:

```text
base_goals_per_team = 1.25   (was 1.3)
elo_lambda_scale    = 800    (goal split softened; elo_scale stays 400)
draw_bias           = 0.08   (parity-aware draw boost)
parity_scale        = 800
```

After calibration (same report, seed 42):

| Metric | v1.3 value |
|--------|-----------|
| Draw rate | 25.5% |
| Goals per match | 2.46 |
| 0-0 rate | 9.8% |
| 1-1 rate | 11.5% |
| Blowouts (3+) | 19.7% (slightly above 18%; accepted, reviewed) |
| Points mass on 1,2,4,5,7 | 56.9% (minimum bucket 7.2%) |
| Favorite win rate (mean) | 60.5% (was 76.4%) |

Favoritism is preserved: top seeds keep 96–99% qualification probability and
the most lopsided fixtures (e.g. `esp` vs `cpv`) stay at ~86% favorite win.

### How to run the diagnostics

```bash
# Full report: analytic match metrics + Monte Carlo points distributions
python scripts/calibration_report.py --runs 10000 --seed 42

# Optional JSON output (gitignored — derived from the premium model)
python scripts/calibration_report.py --runs 1000 --seed 42 --output data/calibration_report.json

# Grid search (75 analytic combinations + MC for the top 5)
python scripts/calibration_report.py --grid --grid-runs 1000 --seed 42

# Ad-hoc what-if without touching model_weights.json
python scripts/calibration_report.py --runs 3000 --seed 42 \
  --base-goals 1.25 --elo-lambda-scale 800 --draw-bias 0.08 --parity-scale 800
```

Match-level metrics are computed exactly from the same adjusted score matrices
the simulator samples from; only the points distributions need Monte Carlo.

### Pending for v1.4

- Matchday-context draw adjustments (`fecha1_caution_draw_boost`,
  `fecha3_context_draw_boost`): require simulating group state after two
  rounds before adjusting matchday-3 incentives.
- Premium outputs (`mc_results.json`, predictions) generated with v1.3 weights
  were exported to Supabase on 2026-06-09 (run
  `7efb36c1-bf6e-4a84-a805-bddace17bfe3`). Re-export whenever squads, XI or
  weights change.
- `26_model_v13_calibration_explainer.sql` updates `get_elo_model_explainer()`
  with the v1.3 parameters; it is written but must still be applied in
  Supabase (the live function still reports the v1.2 values from `25_*.sql`).
- Blowout rate (19.7%) is still slightly above the 18% flag; revisit together
  with PlayerELO features.

---

## Monte Carlo

`scripts/run_monte_carlo.py` runs repeated simulations with:

- `base_goals_per_team` from `model_weights.json`
- `elo_scale` from `model_weights.json`
- `xi_matchup_weight` from `model_weights.json`
- `elo_lambda_scale`, `draw_bias`, `parity_scale` from `model_weights.json` (v1.3)
- strengths from `data/team_strength_snapshots.json`

Output per team includes:

- `qualified_pct`
- `first_pct`
- `second_pct`
- `third_pct`
- `best_third_pct`
- `fourth_pct`
- `points_pct`

`points_pct` is the simulated distribution of final group-stage points over
`0, 1, 2, 3, 4, 5, 6, 7, 9`.

The projected best-third table is one row per group. It shows the most frequent
third-place team for that group, while `avg_pts`, `avg_gd`, `avg_gf`, and
`qualifies_pct` describe the group third-place slot across simulations. Ranking
criteria are currently:

```text
average points > average goal difference > average goals for
```

Pending refinement: if the product needs a team-specific "best third" table,
store separate per-team third-place qualification metrics instead of mixing the
group slot metrics with the most frequent team label.

### Conditioning on played results

Once group matches are played, the projection should reflect reality instead of
re-simulating finished games. `run_monte_carlo.py` accepts `--results-source`:

- `mock` (default) — reads finished group matches from
  `data/match_results.mock.json`.
- `live` — fetches finished rows from the Supabase `match_results` table
  (needs `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`).
- `none` — pure pre-tournament projection, ignores results.

Finished matches (`status == "finished"`, both goals present) use their real
scoreline; only the remaining matches are sampled. The loaders live in
`simulate_group_stage.py` (`load_fixed_results`, `load_fixed_results_live`),
keyed by `match_number`, and orientation is corrected if a result's home/away
is stored inverted relative to the fixture. The output JSON records
`results_source`, `conditioned_matches`, and `fixed_count`. An empty
fixed-results map reproduces the pre-tournament run exactly.

The live-update flow writes a compact local snapshot at
`data/fixed_results.json`:

```json
{
  "fetched_at": "2026-06-24T00:00:00Z",
  "results": {
    "25": [2, 1]
  }
}
```

`run_monte_carlo.py --fixed-results data/fixed_results.json` uses that snapshot
and overrides `--results-source`.

```bash
python scripts/run_monte_carlo.py --runs 20000 --seed 42                      # conditioned on the mock
python scripts/run_monte_carlo.py --runs 20000 --seed 42 --results-source live  # conditioned on the DB
python scripts/run_monte_carlo.py --runs 20000 --seed 42 --fixed-results data/fixed_results.json
```

---

## Knockout / Final Phase

Once the group stage is decided, the 32 qualifiers (top two per group + the eight
best third-placed teams) fill the bracket and each tie is projected round by round
by `scripts/generate_final_phase_predictions.py`.

Inputs:

- `data/knockout_matches.json` — the fixture with slot labels (`homeLabel`,
  `awayLabel`), `matchNum` 73-104, and venue/date per tie.
- `data/fixed_results.json` — real scores loaded so far (from `match_results`),
  used to resolve which team actually occupies each slot.
- `data/team_strength_snapshots.json` + `data/model_weights.json` — the same v1.3
  strengths and weights used for the group stage.

The script reuses the group-stage model components — `elo_probability`
(`top_scoreline_percentages`, 1X2 from the reweighted Poisson matrix),
`xi_matchups` (per-line starter matchup adjustment), and `elo_narrative` (bench
layer + polished editorial prose) — and produces, per tie:

- `team_a_win_probability`, `draw_probability`, `team_b_win_probability`,
- `advance_home_pct` / `advance_away_pct` — knockout has no draws, so the draw
  mass is split between the two sides to yield an advance probability,
- `projected_winner` / `projected_loser`, `global_tag`, and `editorial` text.

Output `data/final_phase_predictions.json` carries `generated_at`, a `source`
block (`fixed_count`, `knockout_fixed_count`, `finished_count`, `model_version`,
`best_third_groups`) and six `rounds`: `r32` (16avos, 16 ties), `r16` (Octavos,
8), `qf` (Cuartos, 4), `sf` (Semifinales, 2), `tp` (Tercer Puesto, 1) and `final`
(1). `js/bracket.js` renders it; non-premium/anon users see flags and slot
positions without percentages via the public `get_bracket_projection()` RPC
(migration `29`).

```bash
# Regenerate the knockout projection after loading more real results
python scripts/generate_final_phase_predictions.py
```

The best-third → slot mapping and previous-round winners/losers are resolved by
`supabase/30_resolve_knockout_best_thirds.sql`; `CURRENT_BEST_THIRD_SLOT_GROUPS`
in the script pins the manual slot assignment for ties whose third-place origin
is already known. Re-run the script whenever a new knockout result lands so the
next round is recomputed with the actual qualifiers.

---

## Validation

Run after any data/model change:

```bash
python scripts/validate_data.py
```

The validator checks:

- 12 groups
- 4 teams per group
- 6 fixtures per group
- 72 matches
- unique `match_id`
- sequential match numbers
- `match_context` entries have `elo_intl` for both team contexts
- `club_adj_weight` is numeric in a valid range
- `xi_matchup_weight` is numeric in a valid range
- `base_goals_per_team` is numeric in a valid range
- `elo_scale` is positive and warns if it differs from the expected `400`
- `elo_lambda_scale` (optional) is numeric in `[100, 2000]`
- `draw_bias` (optional) is numeric in `[0, 0.2]`
- `parity_scale` (optional) is a positive number

`match_context` IDs not present in `matches.json` are currently warnings because
legacy context can still be matched by group, matchday and team pair.

---

## Supabase Export

`scripts/export_to_supabase.py` exports generated rows through the Supabase REST
API using `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`. The service role key is only
for local/admin scripts and must never be committed or loaded in the browser.

The exporter supports `--dry-run`, which does not require credentials and prints
planned writes without secrets.

Examples:

```bash
python scripts/export_to_supabase.py --all --dry-run

python scripts/export_to_supabase.py --predictions --mc-results data/mc_results.json
```

For Monte Carlo snapshots, the exporter:

- deactivates active `simulation_runs` for the same `scenario_name`
- inserts a new active run with `return=representation`
- reads the returned `run_id`
- inserts `simulation_group_standings`
- inserts `simulation_terceros_table` when present in `mc_results.json`

Bulk inserts that do not need a response use minimal return preferences.

### Strengths/MC tail is gated

The strengths + Monte Carlo tail runs only with `--all`, `--strengths`,
`--strengths-only`, or when no selective flag is given. Selective exports
(`--predictions`, `--matches`, `--players`, `--team-profiles`,
`--national-elo`) do **not** run it, so they never insert a new
`simulation_run` as a side effect. Use `--predictions` for a surgical,
text-only refresh of the `predictions` table (probabilities and scorelines
are identical; only the narrative text changes), and `--strengths` to push a
fresh Monte Carlo projection (this is what creates a new active run).

---

## Supabase SQL Order

Minimum order requested for the prediction engine baseline:

```text
01_schema.sql
02_rls.sql
03_functions.sql
05_prediction_engine_schema.sql
07_prediction_engine_rls_hardening.sql
08_security_advisors_hardening.sql
```

For the current full application, continue applying later migrations in numeric
order after that baseline, especially:

```text
09_tournament_core.sql
10_standings_views.sql
11_knockout_rules.sql
12_team_profiles.sql
13_staff_roles.sql
14_simulation_snapshots.sql
15_premium_ops.sql
16_advisor_hardening.sql
17_admin_premium_codes.sql
18_admin_access_monitoring.sql
19_public_profiles_lockdown.sql
20_fix_premium_code_crypto.sql
21_admin_team_content_monitor.sql
22_elo_model_explainer.sql
23_predictions_match_id_unique.sql
24_elo_probability_formula_explainer.sql
25_xi_matchup_model_explainer.sql
26_model_v13_calibration_explainer.sql
```

`05_prediction_engine_schema.sql` creates a public-readable baseline for the
prediction engine tables. Apply `07_prediction_engine_rls_hardening.sql`
afterwards when simulations and player/model outputs are a premium product.
Apply `08_security_advisors_hardening.sql` after function-related SQL to narrow
public function exposure.

---

## Public vs Premium Data

Public:

- tournament fixture/core metadata
- public team profile rows marked `published`
- `national_elo_ratings`, because it mirrors public international ELO data

Premium:

- `predictions`
- `team_strength_snapshots`
- `simulation_runs`
- `simulation_group_standings`
- `simulation_terceros_table`
- `players` when used as a Supabase premium data source
- `team_profile_premium`
- `get_elo_model_explainer()` output

Frontend code must use only the Supabase anon key and rely on RLS. Premium
outputs should be loaded from Supabase for authenticated users with
`profiles.is_premium = true`; local JSON/SQL fallbacks are development-only.

---

## Full Workflow

```bash
python scripts/generate_matches.py
python scripts/validate_data.py
python scripts/build_team_strength.py
python scripts/simulate_group_stage.py --seed 42
python scripts/run_monte_carlo.py --runs 10000 --seed 42 --output data/mc_results.json
python scripts/generate_predictions.py
python scripts/generate_seed_sql.py
python scripts/export_to_supabase.py --all --dry-run
```

Use the non-dry-run export only after confirming the SQL migrations have been
applied and the service role key is available in the local terminal environment.

### Matchday update (a result was played)

When one or more matches finish, provide scores as `match_number:home-away`
tokens. Example: `25:2-1` means match 25 ended home 2, away 1. CSV input is
also supported with `match_number,home_goals,away_goals`.

```bash
# Validate/preview a batch without writing
python scripts/load_results.py 25:2-1 26:0-0 --dry-run --yes

# Full admin flow: load results, fetch all finished group matches, run MC, export only the new MC run
python scripts/update_results.py 25:2-1 26:0-0 --runs 10000 --seed 42

# Re-sync projection from already-loaded Supabase results
python scripts/update_results.py --sync-only --runs 10000 --seed 42

# Knockout stage: after loading a bracket result, recompute the next rounds
python scripts/generate_final_phase_predictions.py
```

Under the hood, `update_results.py` runs:

```bash
python scripts/load_results.py 25:2-1 26:0-0 --yes
python scripts/run_monte_carlo.py --runs 10000 --seed 42 --fixed-results data/fixed_results.json --output data/mc_results.json
python scripts/export_to_supabase.py --mc-only --mc-results data/mc_results.json
```

Notes:
- `predictions` (1X2 + scorelines) do **not** change when a result is played —
  they are pre-match. Only re-run `generate_predictions.py` + the surgical
  `export_to_supabase.py --predictions` if the *narrative/model* changes.
- `data/fixed_results.json` is generated from the live `match_results` table and
  ignored by Git; it replaces manual edits to `data/match_results.mock.json` for
  admin updates.
- `data/mc_results.json` and `data/predictions_seed.sql` are gitignored
  artifacts; they sync to Supabase via the exporter, not via git.

---

## Security Constraints

- Never expose `SUPABASE_SERVICE_KEY` in committed files or frontend code.
- Never modify `redeem_premium_code` without a dedicated security review.
- Do not publish real premium outputs through public static-file fallbacks.
- Browser code must query Supabase with the anon key only; RLS is the access
  boundary.
