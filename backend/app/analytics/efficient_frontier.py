"""Monte Carlo approximation of the efficient frontier (Phase 5).

This is NOT the exact efficient frontier: it filters a finite random sample. Phase 6
computes the frontier by constrained numerical optimization.

Dominance criterion: portfolio j dominates i if vol_j <= vol_i and ret_j >= ret_i with
at least one strict inequality. The filter keeps non-dominated sampled portfolios:
after sorting by volatility (ties: higher return first), a portfolio is kept when its
return exceeds every lower-volatility portfolio's return by more than ``tolerance``.
"""

import numpy as np

FRONTIER_TOLERANCE = 1e-12
LABEL = "Monte Carlo approximation of the efficient frontier (not the exact frontier)"


def non_dominated(
    expected_returns: np.ndarray, volatilities: np.ndarray, *, tolerance: float = FRONTIER_TOLERANCE
) -> np.ndarray:
    """Indices of non-dominated portfolios, ordered by increasing volatility."""
    order = np.lexsort((-expected_returns, volatilities))
    keep = []
    best = -np.inf
    for i in order:
        if expected_returns[i] > best + tolerance:
            keep.append(i)
            best = expected_returns[i]
    return np.asarray(keep, dtype=int)
