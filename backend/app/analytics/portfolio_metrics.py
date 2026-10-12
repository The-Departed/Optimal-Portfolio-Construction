"""Portfolio return, volatility and Sharpe ratio for batches of weight vectors.

Shapes: weights (n_portfolios, n_assets); mu (n_assets,); cov (n_assets, n_assets).
All quantities are annualized decimals; asset order must match across inputs.
"""

import numpy as np

WEIGHT_TOLERANCE = 1e-9
MIN_VOLATILITY = 1e-10


class InvalidWeightsError(ValueError):
    """Weights violate the long-only, fully-invested constraints."""


def validate_weights(weights: np.ndarray, n_assets: int, *, tol: float = WEIGHT_TOLERANCE) -> None:
    if weights.ndim != 2 or weights.shape[1] != n_assets:
        raise InvalidWeightsError(f"expected shape (n, {n_assets}), got {weights.shape}")
    if not np.isfinite(weights).all():
        raise InvalidWeightsError("weights contain non-finite values")
    if (weights < -tol).any() or (weights > 1 + tol).any():
        raise InvalidWeightsError("weights must lie in [0, 1] (no short selling)")
    sums = weights.sum(axis=1)
    if (np.abs(sums - 1.0) > tol).any():
        raise InvalidWeightsError(
            f"weights must sum to 1 (max deviation {np.abs(sums - 1).max():.2e})"
        )


def portfolio_returns(weights: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """R_p = w' mu for each row of ``weights``."""
    return weights @ mu


def portfolio_variances(weights: np.ndarray, cov: np.ndarray, *, tol: float = 1e-12) -> np.ndarray:
    """sigma_p^2 = w' Sigma w for each row.

    Values in [-tol * scale, 0) are floating-point round-off on a PSD matrix and are
    reported as 0; anything more negative means an invalid matrix and raises.
    """
    var = np.einsum("ij,jk,ik->i", weights, cov, weights)
    floor = -tol * max(float(np.abs(cov).max()), 1e-300)
    if (var < floor).any():
        raise ValueError(f"negative portfolio variance {var.min():.3e}: covariance is not PSD")
    return np.where(var < 0, 0.0, var)


def sharpe_ratios(
    returns: np.ndarray,
    volatilities: np.ndarray,
    risk_free: float,
    *,
    min_volatility: float = MIN_VOLATILITY,
) -> np.ndarray:
    """(R_p - R_f) / sigma_p; NaN (undefined) where sigma_p < ``min_volatility``."""
    out = np.full(returns.shape, np.nan)
    ok = volatilities >= min_volatility
    out[ok] = (returns[ok] - risk_free) / volatilities[ok]
    return out
