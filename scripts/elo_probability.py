"""Shared ELO-to-probability helpers for match predictions.

The strength difference controls the expected goal share through the standard
ELO expected-score curve. Total expected goals stay fixed at
2 * base_goals_per_team so large mismatches do not inflate the whole match into
an unrealistic 5-10 expected-goal event.

Calibration layer (model v1.3):

- ``elo_lambda_scale`` decouples the goal-share curve from the win-expectancy
  ``elo_scale``. A larger value softens how fast the goal split leans toward
  the favorite. It is equivalent to the legacy ``10 ** (diff / divisor)`` ratio
  with ``divisor = 2 * elo_lambda_scale``.
- ``adjust_result_probabilities_for_draw`` lifts the draw probability in a
  parity-aware way: the boost is maximal for even matches and fades to zero as
  the strength gap approaches ``parity_scale``.
"""
import math


def elo_expected_score(strength_a, strength_b, elo_scale=400):
    return 1 / (1 + 10 ** (-(strength_a - strength_b) / elo_scale))


def match_lambdas(strength_a, strength_b, base_goals_per_team, elo_scale=400,
                  elo_lambda_scale=None):
    """Split 2 * base_goals_per_team expected goals by ELO expected score.

    ``elo_lambda_scale`` (when provided) replaces ``elo_scale`` only for the
    goal-share curve, so the win-expectancy scale and the goal-split scale can
    be calibrated independently.
    """
    share_scale = elo_lambda_scale if elo_lambda_scale else elo_scale
    expected_a = elo_expected_score(strength_a, strength_b, share_scale)
    total_goals = 2 * base_goals_per_team
    return total_goals * expected_a, total_goals * (1 - expected_a)


def adjust_result_probabilities_for_draw(p_a, p_draw, p_b, draw_bias,
                                         strength_diff, parity_scale=600.0):
    """Parity-aware draw boost over a 1X2 probability triple.

    Pure function. Accepts any non-negative triple (it is normalized first)
    and returns probabilities that sum to 1. The boost is
    ``draw_bias * parity`` where ``parity = max(0, 1 - |diff| / parity_scale)``,
    so even matches get the full boost and clear mismatches keep their draw
    probability almost untouched. The added draw mass is taken from p_a and
    p_b proportionally, and is capped so neither becomes negative.
    """
    total = p_a + p_draw + p_b
    if total <= 0:
        return 0.0, 1.0, 0.0
    pa, pd, pb = p_a / total, p_draw / total, p_b / total

    if draw_bias <= 0 or parity_scale <= 0:
        return pa, pd, pb

    parity = max(0.0, 1.0 - abs(strength_diff) / parity_scale)
    boost = draw_bias * parity
    decisive = pa + pb
    if decisive <= 0:
        return pa, pd, pb
    boost = min(boost, 0.95 * decisive)

    pd_new = pd + boost
    pa_new = pa - boost * (pa / decisive)
    pb_new = pb - boost * (pb / decisive)
    return pa_new, pd_new, pb_new


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
    elo_lambda_scale=None,
    draw_bias=0.0,
    parity_scale=600.0,
):
    lambda_a, lambda_b = match_lambdas(
        strength_a,
        strength_b,
        base_goals_per_team,
        elo_scale,
        elo_lambda_scale,
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

    win_a, draw, win_b = adjust_result_probabilities_for_draw(
        win_a,
        draw,
        win_b,
        draw_bias,
        strength_a - strength_b,
        parity_scale,
    )
    return 100 * win_a, 100 * draw, 100 * win_b


def top_scoreline_percentages(
    strength_a,
    strength_b,
    base_goals_per_team,
    elo_scale=400,
    max_goals=12,
    elo_lambda_scale=None,
    draw_bias=0.0,
    parity_scale=600.0,
    top_n=5,
):
    """Most likely exact scorelines, consistent with the adjusted 1X2 triple.

    Builds the same Poisson score grid used for the outcome probabilities and
    rescales each cell by outcome class (home win / draw / away win) so the
    scoreline masses keep summing to the draw-bias-adjusted 1X2 probabilities.
    Returns a list of ``{"score": "2-1", "pct": 12.4}`` dicts sorted by
    probability (percentage points, one decimal).
    """
    lambda_a, lambda_b = match_lambdas(
        strength_a,
        strength_b,
        base_goals_per_team,
        elo_scale,
        elo_lambda_scale,
    )
    goals_a = poisson_pmf(lambda_a, max_goals)
    goals_b = poisson_pmf(lambda_b, max_goals)

    win_a = draw = win_b = 0.0
    cells = []
    for score_a, prob_a in enumerate(goals_a):
        for score_b, prob_b in enumerate(goals_b):
            probability = prob_a * prob_b
            cells.append((score_a, score_b, probability))
            if score_a > score_b:
                win_a += probability
            elif score_a == score_b:
                draw += probability
            else:
                win_b += probability

    adj_a, adj_draw, adj_b = adjust_result_probabilities_for_draw(
        win_a,
        draw,
        win_b,
        draw_bias,
        strength_a - strength_b,
        parity_scale,
    )
    factor_a = adj_a / win_a if win_a > 0 else 1.0
    factor_draw = adj_draw / draw if draw > 0 else 1.0
    factor_b = adj_b / win_b if win_b > 0 else 1.0

    scored = []
    for score_a, score_b, probability in cells:
        if score_a > score_b:
            probability *= factor_a
        elif score_a == score_b:
            probability *= factor_draw
        else:
            probability *= factor_b
        scored.append((score_a, score_b, probability))

    scored.sort(key=lambda cell: (-cell[2], cell[0] + cell[1], cell[0]))
    return [
        {"score": f"{score_a}-{score_b}", "pct": round(100 * probability, 1)}
        for score_a, score_b, probability in scored[:top_n]
    ]


def rounded_outcome_percentages(
    strength_a,
    strength_b,
    base_goals_per_team,
    elo_scale=400,
    max_goals=12,
    elo_lambda_scale=None,
    draw_bias=0.0,
    parity_scale=600.0,
):
    win_a, draw, win_b = poisson_outcome_probabilities(
        strength_a,
        strength_b,
        base_goals_per_team,
        elo_scale,
        max_goals,
        elo_lambda_scale,
        draw_bias,
        parity_scale,
    )
    win_a = round(win_a, 2)
    draw = round(draw, 2)
    win_b = round(100.0 - win_a - draw, 2)
    if win_b == -0.0:
        win_b = 0.0
    return win_a, draw, win_b
