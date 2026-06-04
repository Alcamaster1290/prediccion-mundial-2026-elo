# Prediction Engine — Technical Reference

## Overview

Python-based ELO simulation engine for the 2026 World Cup group stage. Generates
team strengths from publicly available data, simulates 72 group matches using
Poisson-distributed goal counts, and runs Monte Carlo to produce qualification
probabilities.

**Architecture principle:** Python for all heavy computation, JavaScript only for
display, Supabase for storage and RLS.

---

## Data Files

| File | Purpose |
|------|---------|
| `data/groups.json` | Source of truth — 12 groups, 72 official fixtures |
| `data/matches.json` | Generated (do not edit) — flat list of 72 matches with match_ids |
| `data/match_context.json` | Manual analysis — elo_intl and elo_club_avg for each team |
| `data/teams.json` | Squad data — 26-player lists with club ELOs for analyzed teams |
| `data/club_elo.json` | 197 clubs with ELO scores (worldclubratings.com, 2026-05-26) |
| `data/model_weights.json` | Configurable weights for the strength formula |
| `data/team_strength_snapshots.json` | Generated — team strength scores (do not commit to git if premium) |
| `data/mc_results.json` | Generated — Monte Carlo output (do not commit to git if premium) |
| `data/player_ratings.sample.json` | Sample format for manual player ratings |

---

## Scripts

### `scripts/generate_matches.py`

Reads `data/groups.json` and writes `data/matches.json`. Must be run any time
`groups.json` changes. Match numbering is determined by chronological sort of
date+time (matching `scripts/seed_matches.js` order).

```
python scripts/generate_matches.py
```

**Output fields per match:** `match_id`, `match_number`, `group`, `jornada`,
`date`, `time`, `venue`, `home_team`, `away_team`, `home_name`, `away_name`.

**match_id format:** `grp-{group_lower}-j{jornada}-{home_code}-{away_code}`
e.g. `grp-a-j1-mex-zaf`

---

### `scripts/validate_data.py`

Validates structural integrity of all data files. Run after any data change.

```
python scripts/validate_data.py
```

Checks: 12 groups, 4 teams each, 6 fixtures each, 72 matches total, unique
match_ids, sequential match_numbers, elo_intl present in match_context.json,
model_weights sum to 1.0.

Exit 0 = pass, exit 1 = failures.

---

### `scripts/build_team_strength.py`

Calculates a single strength score per team and writes
`data/team_strength_snapshots.json`.

```
python scripts/build_team_strength.py [--output path]
```

**Strength formula:**

For teams where `elo_club_avg` is available (from `match_context.json`) or
`xi_club_blend` is available (from `teams.json` titulars):

```
strength_score = elo_intl_weight * elo_intl + xi_club_blend_weight * elo_club_avg
```

For all other teams: `strength_score = elo_intl`

Default weights (`data/model_weights.json`): `elo_intl_weight = 0.65`,
`xi_club_blend_weight = 0.35`.

---

### `scripts/simulate_group_stage.py`

Runs one deterministic (or seeded) group stage simulation. Also importable as
a module.

```
python scripts/simulate_group_stage.py [--seed 42]
```

**Goal generation algorithm:**

For a match between team A (strength `s_a`) and team B (strength `s_b`):

```
factor   = 10 ^ ( (s_a - s_b) / 800 )
lambda_a = base_goals_per_team * factor
lambda_b = base_goals_per_team / factor
goals_a  = Poisson(lambda_a)    # Knuth algorithm
goals_b  = Poisson(lambda_b)
```

The divisor 800 is `2 * elo_scale` (400). Using the square root of the ELO
ratio keeps the geometric mean of both lambdas constant at `base_goals_per_team`.

**Tiebreaker:** PTS → GD → GF → draw/pot order (same as `standings.js`).

**Importable API:**

```python
from simulate_group_stage import simulate_all_groups, load_matches, load_strengths, best_thirds

matches   = load_matches()
strengths = load_strengths()
standings = simulate_all_groups(matches, strengths, base_goals=1.3)
top8      = best_thirds(standings)[:8]
```

---

### `scripts/run_monte_carlo.py`

Runs N independent simulations and aggregates qualification probabilities.

```
python scripts/run_monte_carlo.py --runs 1000 --seed 42 --output data/mc_results.json
```

**Arguments:**

| Flag | Default | Description |
|------|---------|-------------|
| `--runs` | 1000 | Number of simulations |
| `--seed` | None | Random seed (omit for non-reproducible) |
| `--output` | `data/mc_results.json` | Output file path |

**Output schema:**

```json
{
  "runs": 1000,
  "seed": 42,
  "teams": {
    "bra": {
      "qualified_pct": 100.0,
      "first_pct": 71.4,
      "second_pct": 25.0,
      "third_pct": 3.6,
      "best_third_pct": 3.6,
      "fourth_pct": 0.0,
      "points_pct": {
        "0": 0.0,
        "1": 0.0,
        "2": 0.0,
        "3": 1.2,
        "4": 4.8,
        "5": 0.0,
        "6": 18.6,
        "7": 24.0,
        "9": 51.4
      }
    }
  }
}
```

`qualified_pct = first_pct + second_pct + best_third_pct`
`points_pct` is the simulated distribution for total group-stage points.

---

### `scripts/export_to_supabase.py`

Exports `team_strength_snapshots.json` and `mc_results.json` to Supabase.
Uses stdlib `urllib` — no external dependencies.

```
SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=<service_role_key> \
  python scripts/export_to_supabase.py

# Strengths only (skip MC results):
python scripts/export_to_supabase.py --strengths-only
```

**Security:** Requires `SUPABASE_SERVICE_KEY` (service_role). Never commit this
key to the repository.

---

## Supabase Schema

Defined in `supabase/05_prediction_engine_schema.sql`. Apply via Supabase MCP or
the Supabase CLI, then apply `supabase/07_prediction_engine_rls_hardening.sql`
if the prediction engine should remain premium-only. Apply
`supabase/08_security_advisors_hardening.sql` after function-related SQL to keep
advisor findings limited to intentional/auth-dashboard settings.

Tables added (do not modify existing tables):

| Table | Description |
|-------|-------------|
| `team_strength_snapshots` | Strength scores per team per version |
| `simulation_runs` | Monte Carlo run metadata |
| `simulation_group_standings` | Aggregated qualification percentages per run |
| `players` | Optional supplement to `data/teams.json` |

`05_prediction_engine_schema.sql` creates a public-readable baseline with
explicit Data API grants. `07_prediction_engine_rls_hardening.sql` replaces that
with premium-only reads for `authenticated` users whose profile has
`is_premium = true`, revokes `anon` table access, and keeps `service_role`
write permissions for export scripts.

---

## Full Workflow

```bash
# 1. Generate match list from fixture data
python scripts/generate_matches.py

# 2. Validate all data files
python scripts/validate_data.py

# 3. Build team strength scores
python scripts/build_team_strength.py

# 4. Quick single simulation (sanity check)
python scripts/simulate_group_stage.py --seed 42

# 5. Run Monte Carlo (1000 simulations)
python scripts/run_monte_carlo.py --runs 1000 --seed 42

# 6. Export to Supabase (requires service key)
SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=... python scripts/export_to_supabase.py
```

---

## Security Constraints

- **Never expose `SUPABASE_SERVICE_KEY`** in any committed file.
- **Never modify `redeem_premium_code`** RPC function (`supabase/03_functions.sql`).
- The `predictions` table (match probability narratives) is premium-only via RLS.
  Do not store detailed predictions in `simulation_group_standings`.
- `mc_results.json` and `team_strength_snapshots.json` contain derived data — they
  are safe to publish if not tied to premium subscriptions. Keep them out of git
  if they represent a premium product differentiator.

---

## Adding More Teams to Squad Analysis

1. Add the team to `data/teams.json` following the existing BIH/KOR/JPN structure.
2. For each player, set `"elo"` to their club's ELO from `data/club_elo.json`.
3. Set `"titular": true` for the expected starting XI.
4. Run `python scripts/build_team_strength.py` — the team will automatically use
   the weighted blend method instead of elo_intl only.

---

## Running Tests

```bash
pytest
```

Test files should be placed in `tests/` following the naming convention
`test_<module>.py`.
