"""Shared ELO-to-probability helpers for match predictions.

The strength difference controls the expected goal share through the standard
ELO expected-score curve. Total expected goals stay fixed at
2 * base_goals_per_team so large mismatches do not inflate the whole match into
an unrealistic 5-10 expected-goal event.
"""
import math


def elo_expected_score(strength_a, strength_b, elo_scale=400):
    return 1 / (1 + 10 ** (-(strength_a - strength_b) / elo_scale))


def match_lambdas(strength_a, strength_b, base_goals_per_team, elo_scale=400):
    expected_a = elo_expected_score(strength_a, strength_b, elo_scale)
    total_goals = 2 * base_goals_per_team
    return total_goals * expected_a, total_goals * (1 - expected_a)


def poisson_pmf(lam, max_goals):
    return [
        math.exp(-lam) * (lam ** goals) / math.factorial(goals)
        for goals in range(max_goals + 1)
    ]


def poisson_outcome_probabilities(
    strength_a,
    strength_b,
    base_goals_per_team,
    elo_scale=400,
    max_goals=12,
):
    lambda_a, lambda_b = match_lambdas(
        strength_a,
        strength_b,
        base_goals_per_team,
        elo_scale,
    )
    goals_a = poisson_pmf(lambda_a, max_goals)
    goals_b = poisson_pmf(lambda_b, max_goals)

    win_a = draw = win_b = 0.0
    for score_a, prob_a in enumerate(goals_a):
        for score_b, prob_b in enumerate(goals_b):
            probability = prob_a * prob_b
            if score_a > score_b:
                win_a += probability
            elif score_a == score_b:
                draw += probability
            else:
                win_b += probability

    total = win_a + draw + win_b
    if total <= 0:
        return 0.0, 100.0, 0.0
    return 100 * win_a / total, 100 * draw / total, 100 * win_b / total


def rounded_outcome_percentages(
    strength_a,
    strength_b,
    base_goals_per_team,
    elo_scale=400,
    max_goals=12,
):
    win_a, draw, win_b = poisson_outcome_probabilities(
        strength_a,
        strength_b,
        base_goals_per_team,
        elo_scale,
        max_goals,
    )
    win_a = round(win_a, 2)
    draw = round(draw, 2)
    win_b = round(100.0 - win_a - draw, 2)
    if win_b == -0.0:
        win_b = 0.0
    return win_a, draw, win_b
