"""
Statistical utilities for nupunkt.

This module provides statistical functions used in the Punkt algorithm
for calculating log-likelihood and related measurements.
"""

import math


def dunning_log_likelihood(count_a: int, count_b: int, count_ab: int, N: int) -> float:
    """
    Modified Dunning log-likelihood calculation that gives higher weight to
    potential abbreviations. This makes the model more likely to detect abbreviations,
    especially in larger datasets where evidence may be diluted.

    Args:
        count_a: Count of event A (e.g., token appears)
        count_b: Count of event B (e.g., token appears with period)
        count_ab: Count of events A and B together
        N: Total count of all events

    Returns:
        The log likelihood score (higher means more significant)
    """
    # Handle edge case where N is zero
    if N == 0:
        return 0.0

    # Clamp to [0, 1]: with pruned or incrementally updated frequency distributions
    # count_b can exceed N, which would otherwise raise a math domain error.
    p1 = min(max(count_b / N, 0.0), 1.0)
    p2 = 0.99
    null_hypo = count_ab * math.log(p1 + 1e-8) + (count_a - count_ab) * math.log(1.0 - p1 + 1e-8)
    alt_hypo = count_ab * math.log(p2) + (count_a - count_ab) * math.log(1.0 - p2)

    # Basic log likelihood calculation
    ll = -2.0 * (null_hypo - alt_hypo)

    # Boosting factor for short tokens (likely abbreviations)
    # This makes the algorithm more sensitive to abbreviation detection
    return ll * 1.5


def collocation_log_likelihood(count_a: int, count_b: int, count_ab: int, N: int) -> float:
    """
    Calculate the log-likelihood ratio for collocations.

    Args:
        count_a: Count of the first token
        count_b: Count of the second token
        count_ab: Count of the collocation (first and second token together)
        N: Total number of tokens

    Returns:
        The log likelihood score for the collocation
    """
    # Handle edge case where N is zero
    if N == 0:
        return 0.0

    p = min(max(count_b / N, 0.0), 1.0)
    p1 = count_ab / count_a if count_a else 0
    try:
        p2 = (count_b - count_ab) / (N - count_a) if (N - count_a) else 0
    except ZeroDivisionError:
        p2 = 1
    try:
        summand1 = count_ab * math.log(p) + (count_a - count_ab) * math.log(1.0 - p)
    except ValueError:
        summand1 = 0
    try:
        summand2 = (count_b - count_ab) * math.log(p) + (
            N - count_a - count_b + count_ab
        ) * math.log(1.0 - p)
    except ValueError:
        summand2 = 0
    summand3 = (
        0
        if count_a == count_ab or p1 <= 0 or p1 >= 1
        else count_ab * math.log(p1) + (count_a - count_ab) * math.log(1.0 - p1)
    )
    summand4 = (
        0
        if count_b == count_ab or p2 <= 0 or p2 >= 1
        else (count_b - count_ab) * math.log(p2)
        + (N - count_a - count_b + count_ab) * math.log(1.0 - p2)
    )
    return -2.0 * (summand1 + summand2 - summand3 - summand4)
