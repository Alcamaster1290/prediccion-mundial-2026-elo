#!/usr/bin/env python3
"""Monte Carlo simulation of the 2026 World Cup knockout bracket.

Unlike ``run_monte_carlo.py`` (which only simulates the group stage), this
script plays out the remaining knockout ties thousands of times to produce
cumulative advancement probabilities per team: reach round of 16 / quarters /
semis / final, become champion, and win the third-place match.

Ties already decided in ``data/fixed_results.json`` are held fixed; only the
pending matches are sampled. Each pending tie uses the SAME model as
``generate_final_phase_predictions.py`` — matchup-adjusted ELO strengths ->
Poisson 1X2 -> draw split into a penalty-shootout probability — so the per-tie
odds are identical to the ones shown on the bracket, just propagated forward.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "knockout_mc_results.json"

from generate_final_phase_predictions import (  # noqa: E402
    advance_split,
    best_thirds,
    build_group_standings,
    build_team_names,
    build_third_assignments,
    knockout_match_ref,
    load_fixed_result_records,
    load_json,
    orient_result,
    resolve_r32_team,
    result_winner,
    split_fixed_results,
)
from generate_predictions import match_probs  # noqa: E402
from xi_matchups import build_xi_profiles, matchup_adjusted_strengths  # noqa: E402

# Rounds a winner is promoted INTO, and the phase whose participants define
# "reached this round". r32 participants are the 32 qualifiers (deterministic).
REACH_PHASES = ["r16", "qf", "sf", "final"]


class BracketModel:
    """Resolves the bracket topology and pairwise advance probabilities once,
    then samples winners for pending ties on demand."""

    def __init__(self, fixed_results_path=None):
        matches = load_json(DATA_DIR / "matches.json")
        fixed_results_path = Path(fixed_results_path) if fixed_results_path else DATA_DIR / "fixed_results.json"
        fixed_records = load_fixed_result_records(fixed_results_path, matches)
        group_results, knockout_results = split_fixed_results(fixed_records)
        self.knockout_matches = sorted(
            load_json(DATA_DIR / "knockout_matches.json"), key=lambda item: item["matchNum"]
        )
        teams_data = load_json(DATA_DIR / "teams.json")
        strengths = load_json(DATA_DIR / "team_strength_snapshots.json")
        self.weights = load_json(DATA_DIR / "model_weights.json")

        standings = build_group_standings(matches, group_results)
        thirds = best_thirds(standings)
        third_assignments = build_third_assignments(self.knockout_matches, thirds)

        self.names = build_team_names(teams_data)
        self.xi_profiles = build_xi_profiles(teams_data)
        self.strengths = strengths["teams"]
        self.model_version = strengths.get("_version", self.weights.get("version", "1.3"))
        self.knockout_fixed_count = len(knockout_results)
        # Teams that lost a decided knockout tie are out of contention.
        self.eliminated = set()

        # Per-match topology: how each side is fed, and the fixed winner if played.
        # feeders[num] = {"home": ("team", code) | ("W", src) | ("L", src),
        #                 "away": (...), "phase": ..., "fixed_winner": code|None,
        #                 "fixed_loser": code|None}
        self.feeders = {}
        self._advance_cache = {}

        for match in self.knockout_matches:
            num = match["matchNum"]
            if match["phase"] == "r32":
                home_row = resolve_r32_team(match["homeLabel"], num, "homeLabel", standings, third_assignments)
                away_row = resolve_r32_team(match["awayLabel"], num, "awayLabel", standings, third_assignments)
                home_side = ("team", home_row["code"])
                away_side = ("team", away_row["code"])
            else:
                home_side = self._parse_feeder(match.get("homeLabel"))
                away_side = self._parse_feeder(match.get("awayLabel"))

            fixed_winner = fixed_loser = None
            result = knockout_results.get(num)
            if result:
                # Concrete teams are needed to orient the stored result.
                home_code = home_side[1] if home_side[0] == "team" else None
                away_code = away_side[1] if away_side[0] == "team" else None
                if home_code and away_code:
                    oriented = orient_result(result, home_code, away_code)
                    fixed_winner = result_winner(oriented, home_code, away_code)
                    fixed_loser = away_code if fixed_winner == home_code else home_code
                else:
                    # Winner is stored explicitly on knockout rows.
                    fixed_winner = result.get("winner_team")

            self.feeders[num] = {
                "phase": match["phase"],
                "home": home_side,
                "away": away_side,
                "fixed_winner": fixed_winner,
                "fixed_loser": fixed_loser,
            }

        self._resolve_fixed_losers()

    def _resolve_fixed_losers(self):
        """Forward pass over decided ties only, propagating actual winners so the
        loser of every played match (including W:-fed rounds) can be identified
        and marked eliminated."""
        actual_winners = {}
        actual_losers = {}
        for match in self.knockout_matches:
            num = match["matchNum"]
            info = self.feeders[num]
            home = self.resolve_side(info["home"], actual_winners, actual_losers)
            away = self.resolve_side(info["away"], actual_winners, actual_losers)
            if not info["fixed_winner"]:
                continue  # pending tie: stop propagating down this path
            winner = info["fixed_winner"]
            actual_winners[num] = winner
            if home and away:
                loser = away if winner == home else home
                info["fixed_loser"] = loser
                actual_losers[num] = loser
                self.eliminated.add(loser)

    @staticmethod
    def _parse_feeder(label):
        win = knockout_match_ref(label, "winner")
        if win is not None:
            return ("W", win)
        loss = knockout_match_ref(label, "loser")
        if loss is not None:
            return ("L", loss)
        raise ValueError(f"Unrecognized knockout feeder label: {label!r}")

    def advance_prob(self, home, away):
        """P(home advances) for a single tie, identical to the bracket model."""
        key = (home, away)
        cached = self._advance_cache.get(key)
        if cached is not None:
            return cached
        w = self.weights
        base_goals = w["base_goals_per_team"]
        elo_scale = w.get("elo_scale", 400)
        max_goals = w.get("poisson_max_goals", 12)
        xi_matchup_weight = w.get("xi_matchup_weight", 0.20)
        elo_lambda_scale = w.get("elo_lambda_scale")
        draw_bias = w.get("draw_bias", 0.0)
        parity_scale = w.get("parity_scale", 600.0)

        s_home = self.strengths.get(home, {}).get("strength_score", 1500.0)
        s_away = self.strengths.get(away, {}).get("strength_score", 1500.0)
        eff_home, eff_away, _ = matchup_adjusted_strengths(
            home, away, s_home, s_away, self.xi_profiles, xi_matchup_weight=xi_matchup_weight
        )
        pa, pd, pb = match_probs(
            eff_home, eff_away, base_goals, elo_scale=elo_scale, max_goals=max_goals,
            elo_lambda_scale=elo_lambda_scale, draw_bias=draw_bias, parity_scale=parity_scale,
        )
        adv_home, _ = advance_split(pa, pd, pb, eff_home, eff_away)
        prob = adv_home / 100.0
        self._advance_cache[key] = prob
        return prob

    def resolve_side(self, side, winners, losers):
        kind, ref = side
        if kind == "team":
            return ref
        if kind == "W":
            return winners.get(ref)
        return losers.get(ref)

    def simulate_once(self, rng):
        """Play the whole bracket once. Returns (winners, losers, participants)
        where participants[phase] is the set of team codes playing that round."""
        winners = {}
        losers = {}
        participants = defaultdict(set)
        for match in self.knockout_matches:
            num = match["matchNum"]
            info = self.feeders[num]
            home = self.resolve_side(info["home"], winners, losers)
            away = self.resolve_side(info["away"], winners, losers)
            if home is None or away is None:
                raise RuntimeError(f"Cannot resolve participants for match {num}")
            participants[info["phase"]].add(home)
            participants[info["phase"]].add(away)

            if info["fixed_winner"]:
                winner = info["fixed_winner"]
                loser = info["fixed_loser"] or (away if winner == home else home)
            else:
                winner = home if rng.random() < self.advance_prob(home, away) else away
                loser = away if winner == home else home
            winners[num] = winner
            losers[num] = loser
        return winners, losers, participants


def simulate(model, runs, seed):
    rng = random.Random(seed)
    reach = defaultdict(lambda: defaultdict(int))  # code -> metric -> count
    alive = set()

    # Final match number is the highest; third-place is phase "tp".
    final_num = max(m["matchNum"] for m in model.knockout_matches if m["phase"] == "final")
    tp_num = next((m["matchNum"] for m in model.knockout_matches if m["phase"] == "tp"), None)

    for _ in range(runs):
        winners, losers, participants = model.simulate_once(rng)
        for phase in REACH_PHASES:
            for code in participants.get(phase, ()):  # participated in this round
                reach[code]["reach_" + phase] += 1
        champion = winners.get(final_num)
        if champion:
            reach[champion]["champion"] += 1
        if tp_num is not None and winners.get(tp_num):
            reach[winners[tp_num]]["third_place"] += 1
        for code in participants.get("r16", ()):
            alive.add(code)
        for code in participants.get("qf", ()):
            alive.add(code)

    metrics = ["reach_" + p for p in REACH_PHASES] + ["champion", "third_place"]
    teams = []
    for code in alive:
        row = {
            "code": code,
            "name": model.names.get(code, code.upper()),
            "alive": code not in model.eliminated,
        }
        for metric in metrics:
            row[metric] = round(100.0 * reach[code][metric] / runs, 1)
        teams.append(row)
    # Still-alive teams first, then by title odds.
    teams.sort(key=lambda r: (not r["alive"], -r["champion"], -r["reach_final"], -r["reach_sf"]))
    return teams, metrics


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo knockout bracket simulation")
    parser.add_argument("--runs", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fixed-results", default=str(DATA_DIR / "fixed_results.json"))
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    parser.add_argument("--print", dest="do_print", action="store_true", help="Print a summary table")
    args = parser.parse_args()

    model = BracketModel(fixed_results_path=args.fixed_results)
    teams, metrics = simulate(model, args.runs, args.seed)

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runs": args.runs,
        "seed": args.seed,
        "source": {
            "knockout_fixed_count": model.knockout_fixed_count,
            "model_version": model.model_version,
        },
        "metrics": metrics,
        "teams": teams,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    alive_count = sum(1 for row in teams if row["alive"])
    print(f"Simulated {args.runs} knockout runs -> {args.output} ({alive_count} alive / {len(teams)} teams)")

    if args.do_print:
        print(f"\n{'Team':16}{'R16':>7}{'QF':>7}{'SF':>7}{'Final':>8}{'Champ':>8}{'3rd':>7}")
        for row in teams:
            if not row["alive"]:
                break  # eliminated teams follow; skip in the summary
            print(f"{row['name'][:15]:16}"
                  f"{row['reach_r16']:>7}{row['reach_qf']:>7}{row['reach_sf']:>7}"
                  f"{row['reach_final']:>8}{row['champion']:>8}{row['third_place']:>7}")


if __name__ == "__main__":
    main()
