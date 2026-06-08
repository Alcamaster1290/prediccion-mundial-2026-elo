# Prediction Engine - Technical Reference

## Overview

Python-based ELO simulation engine for the 2026 World Cup group stage. The
pipeline builds team strengths from public international ELO plus sourced club
ELO for expected starters, applies a small starter line-matchup adjustment per
match, simulates group matches with Poisson goal counts, and exports premium
outputs to Supabase.

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

Generated premium outputs are ignored by Git and should be regenerated locally
when needed, then exported to Supabase. Do not publish them as public static
assets in production.

---

## Model Weights

`data/model_weights.json` is the single source for model constants:

| Field | Current meaning |
|-------|-----------------|
| `_version` | Model/data version written to generated outputs. Current value: `1.2`. |
| `_note` | Human-readable summary of the model formula. |
| `club_adj_weight` | Weight applied to the starter XI club-ELO delta against the global XI average. |
| `xi_matchup_weight` | Weight applied per match to starter line matchup edges. |
| `base_goals_per_team` | Half of the fixed expected-goals total used by Poisson probabilities. |
| `elo_scale` | ELO logistic scale. Expected and preferred value is `400`. |

The old fields `elo_intl_weight` and `xi_club_blend_weight` are obsolete. Model
weights do not sum to `1.0`; the current formula is an additive adjustment on
the international ELO scale.

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
total:

```text
expected_a = 1 / (1 + 10 ^ (-(strength_a - strength_b) / elo_scale))
total_goals = 2 * base_goals_per_team
lambda_a = total_goals * expected_a
lambda_b = total_goals * (1 - expected_a)
```

This replaces the older `base_goals * 10^(diff / 800)` description. If the
legacy divisor `800` appears in old notes, interpret it as the old square-root
ratio equivalent of `2 * elo_scale`; the active code reads `elo_scale` directly.

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

## Monte Carlo

`scripts/run_monte_carlo.py` runs repeated simulations with:

- `base_goals_per_team` from `model_weights.json`
- `elo_scale` from `model_weights.json`
- `xi_matchup_weight` from `model_weights.json`
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

---

## Security Constraints

- Never expose `SUPABASE_SERVICE_KEY` in committed files or frontend code.
- Never modify `redeem_premium_code` without a dedicated security review.
- Do not publish real premium outputs through public static-file fallbacks.
- Browser code must query Supabase with the anon key only; RLS is the access
  boundary.
