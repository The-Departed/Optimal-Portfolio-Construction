"""Reproducible Monte Carlo sampling of long-only, fully-invested portfolios.

Weights are drawn from a symmetric Dirichlet(alpha) distribution (alpha = 1 is the
uniform distribution on the simplex): every draw satisfies w_i > 0 and sum(w) = 1 by
construction, and is still validated. Results depend only on the inputs, the number
of portfolios and the seed (``numpy.random.default_rng``).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analytics.covariance import diagnose
from app.analytics.portfolio_metrics import (
    portfolio_returns,
    portfolio_variances,
    sharpe_ratios,
    validate_weights,
)


class SimulationInputError(ValueError):
    """Inputs (expected returns, covariance, parameters) are invalid for simulation."""


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    n_portfolios: int
    seed: int
    dirichlet_alpha: float = 1.0
    max_portfolios: int = 200_000


@dataclass(frozen=True)
class SimulationResult:
    config: SimulationConfig
    asset_ids: tuple[str, ...]
    weights: np.ndarray
    expected_returns: np.ndarray
    volatilities: np.ndarray
    sharpe: np.ndarray
    risk_free: float

    @property
    def sharpe_defined(self) -> np.ndarray:
        return np.isfinite(self.sharpe)

    @property
    def min_volatility_index(self) -> int:
        return int(np.argmin(self.volatilities))

    @property
    def max_sharpe_index(self) -> int | None:
        if not self.sharpe_defined.any():
            return None
        return int(np.nanargmax(self.sharpe))

    def frame(self) -> pd.DataFrame:
        df = pd.DataFrame(self.weights, columns=[f"w_{a}" for a in self.asset_ids])
        df.insert(0, "portfolio_id", np.arange(len(df)))
        df["expected_return"] = self.expected_returns
        df["volatility"] = self.volatilities
        df["sharpe_ratio"] = self.sharpe
        return df


def validate_inputs(mu: pd.Series, cov: pd.DataFrame, config: SimulationConfig) -> None:
    if not 1 <= config.n_portfolios <= config.max_portfolios:
        raise SimulationInputError(f"n_portfolios must be between 1 and {config.max_portfolios}")
    if config.seed < 0:
        raise SimulationInputError("seed must be non-negative")
    if not config.dirichlet_alpha > 0:
        raise SimulationInputError("dirichlet_alpha must be positive")
    if len(mu) < 2:
        raise SimulationInputError("at least two assets are required")
    if list(mu.index) != list(cov.index) or list(cov.index) != list(cov.columns):
        raise SimulationInputError(
            "expected returns and covariance must share the same asset order"
        )
    if not np.isfinite(mu.to_numpy()).all():
        raise SimulationInputError("expected returns contain non-finite values")
    diag = diagnose(cov, observations=0, kind="covariance")
    if not diag.valid:
        raise SimulationInputError("invalid covariance matrix: " + "; ".join(diag.problems()))


def dirichlet_weights(n: int, k: int, seed: int, alpha: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.dirichlet(np.full(k, alpha), size=n)


def simulate(
    mu: pd.Series, cov: pd.DataFrame, risk_free: float, config: SimulationConfig
) -> SimulationResult:
    validate_inputs(mu, cov, config)
    if not np.isfinite(risk_free):
        raise SimulationInputError("risk-free rate must be finite")
    k = len(mu)
    weights = dirichlet_weights(config.n_portfolios, k, config.seed, config.dirichlet_alpha)
    validate_weights(weights, k)
    rets = portfolio_returns(weights, mu.to_numpy(dtype="float64"))
    vols = np.sqrt(portfolio_variances(weights, cov.to_numpy(dtype="float64")))
    sharpe = sharpe_ratios(rets, vols, risk_free)
    if not (np.isfinite(rets).all() and np.isfinite(vols).all()):
        raise SimulationInputError("non-finite portfolio metrics")
    return SimulationResult(
        config=config,
        asset_ids=tuple(str(a) for a in mu.index),
        weights=weights,
        expected_returns=rets,
        volatilities=vols,
        sharpe=sharpe,
        risk_free=risk_free,
    )


def distribution_summary(values: np.ndarray) -> dict[str, float]:
    v = values[np.isfinite(values)]
    q = np.quantile(v, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "min": float(v.min()),
        "p05": float(q[0]),
        "p25": float(q[1]),
        "median": float(q[2]),
        "p75": float(q[3]),
        "p95": float(q[4]),
        "max": float(v.max()),
        "mean": float(v.mean()),
        "std": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
    }
