# ELO XI Imputation Design

## Context

The current hybrid ELO model averages only starters with a known club ELO. That creates bias when coverage is uneven: a team with 1 known starter can receive an XI adjustment from a single player, while missing starters are silently ignored.

The model should remain fair to teams whose players are in clubs outside the club ELO source, while avoiding inflation from tiny samples.

## Approved Approach

Use an international-ELO-derived prior for missing starter club ELO values, then shrink the club-based adjustment by data coverage.

For each analyzed team:

```text
known_starters = starters with club ELO
missing_starters = 11 - known_starters
intl_delta = elo_intl - avg_elo_intl_analyzed
prior_nd = clamp(avg_xi_blend + intl_delta * prior_intl_weight, min_prior_elo, max_prior_elo)
xi_imputed = (sum_known_elo + missing_starters * prior_nd) / 11
confidence = known_starters / 11
score = elo_intl + (xi_imputed - avg_xi_blend) * club_adj_weight * confidence
```

Defaults:

```json
{
  "club_adj_weight": 0.35,
  "prior_intl_weight": 0.35,
  "min_starter_elo_for_full_xi": 8,
  "min_prior_elo": 1250,
  "max_prior_elo": 1850
}
```

## Data Flow

`data/teams.json` remains the source for player rows and true known club ELO values.

`scripts/build_team_strength.py` calculates:

- observed starter ELO count
- prior for missing starter ELOs
- imputed XI blend
- confidence-adjusted team strength score

`data/team_strength_snapshots.json` stores the generated `xi_blend` as the imputed XI value used by the score. The score remains the value consumed by match predictions and Monte Carlo simulation.

Supabase export remains centered on:

- `players`: real player data and known `elo_club` values
- `team_strength_snapshots`: generated `elo_club_avg`, `strength_score`, and `method`
- `simulation_runs`, `simulation_group_standings`, `simulation_terceros_table`, and `predictions`: regenerated after strength changes

## Expected Behavior

South Korea has high coverage, so its adjustment remains mostly driven by the 9 known starters while its 2 missing starters receive a reasonable national-strength prior.

Curacao has low coverage, so the single known PSV starter no longer dominates the XI. The missing starters receive a national-strength prior, but the final club adjustment is heavily reduced by confidence.

Teams with no player data continue to use `elo_intl_only`.

## Testing

Add focused tests for:

- missing starters are imputed instead of ignored
- low-coverage teams receive a smaller adjustment than the old single-sample behavior
- high-coverage teams keep a larger share of their observed XI signal
- teams without analyzed player data still use `elo_intl_only`

Run data validation and the affected Python tests after implementation.
