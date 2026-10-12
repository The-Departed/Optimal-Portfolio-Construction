"""Constrained long-only portfolio optimization (Phase 6) with SciPy SLSQP.

All three profiles are convex problems:

* conservative: minimize w' Sigma w                        (convex QP)
* balanced:     maximize (w' mu - R_f) / sqrt(w' Sigma w)  (solved via the convex
                rescaling y = w / k: minimize y' Sigma y s.t. (mu - R_f)' y = 1, y >= 0,
                then w = y / sum(y); valid when some mu_i > R_f), cross-checked by
                direct maximization from several starting portfolios
* growth:       maximize w' mu s.t. w' Sigma w <= sigma_max^2   (convex)

subject to sum(w) = 1 and 0 <= w_i <= 1. Because the problems are convex, a solution
that passes the feasibility checks is a global optimum up to solver tolerance. Every
start is recorded; a run that fails the checks is never returned as a solution.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.analytics.covariance import diagnose
from app.analytics.portfolio_metrics import MIN_VOLATILITY

SOLVER = "scipy.optimize.minimize (method='SLSQP')"


class OptimizationInputError(ValueError):
    """Inputs (mu, Sigma, R_f, sigma_max) are invalid for optimization."""


class InfeasibleProblemError(ValueError):
    """No long-only portfolio satisfies the requested constraint."""

    def __init__(self, message: str, *, minimum_volatility: float) -> None:
        super().__init__(message)
        self.minimum_volatility = minimum_volatility


class SolverFailedError(RuntimeError):
    """No start converged to a solution that passes the feasibility checks."""

    def __init__(self, message: str, attempts: list["StartResult"]) -> None:
        super().__init__(message)
        self.attempts = attempts


@dataclass(frozen=True, slots=True)
class SolverConfig:
    ftol: float = 1e-12
    maxiter: int = 1_000
    random_starts: int = 6
    start_seed: int = 20_240_101
    weight_tolerance: float = 1e-8  # max |sum(w) - 1| and bound violation before cleanup
    volatility_tolerance: float = 1e-8  # allowed excess over sigma_max (absolute)

    def describe(self) -> dict[str, object]:
        return {
            "solver": SOLVER,
            "ftol": self.ftol,
            "maxiter": self.maxiter,
            "random_starts": self.random_starts,
            "start_seed": self.start_seed,
            "weight_tolerance": self.weight_tolerance,
            "volatility_tolerance": self.volatility_tolerance,
        }


DEFAULT_CONFIG = SolverConfig()


@dataclass(frozen=True, slots=True)
class StartResult:
    label: str
    success: bool
    accepted: bool
    message: str
    iterations: int
    evaluations: int
    objective: float | None


@dataclass(frozen=True)
class Solution:
    weights: np.ndarray
    expected_return: float
    volatility: float
    sharpe: float | None
    objective: float
    best_start: str
    iterations: int
    sum_residual: float  # |sum(w) - 1| of the raw solver output
    bound_violation: float  # max violation of 0 <= w <= 1 in the raw solver output
    attempts: list[StartResult] = field(default_factory=list)
    volatility_slack: float | None = None  # sigma_max - volatility (growth only)
    verification: dict[str, float] = field(default_factory=dict)


def validate_inputs(mu: np.ndarray, cov: np.ndarray, risk_free: float, labels: list[str]) -> None:
    n = len(labels)
    if mu.shape != (n,) or cov.shape != (n, n):
        raise OptimizationInputError(f"expected {n} returns and a {n}x{n} covariance matrix")
    if not np.isfinite(mu).all():
        raise OptimizationInputError("expected returns contain non-finite values")
    if not np.isfinite(risk_free):
        raise OptimizationInputError("risk-free rate must be finite")
    diag = diagnose(pd.DataFrame(cov, index=labels, columns=labels), 0, kind="covariance")
    if not diag.valid:
        raise OptimizationInputError("invalid covariance matrix: " + "; ".join(diag.problems()))


def metrics(
    w: np.ndarray, mu: np.ndarray, cov: np.ndarray, risk_free: float
) -> tuple[float, float, float | None]:
    ret = float(w @ mu)
    vol = float(np.sqrt(max(float(w @ cov @ w), 0.0)))
    sharpe = (ret - risk_free) / vol if vol >= MIN_VOLATILITY else None
    return ret, vol, sharpe


def _clean(w: np.ndarray, tol: float) -> tuple[np.ndarray, float, float] | None:
    """Accept raw solver output only if it is feasible within ``tol``.

    Returns the weights clipped to [0, 1] and renormalized (removing round-off only),
    with the raw sum residual and bound violation; ``None`` if infeasible.
    """
    if not np.isfinite(w).all():
        return None
    residual = abs(float(w.sum()) - 1.0)
    violation = float(max(0.0, -w.min(), w.max() - 1.0))
    if residual > tol or violation > tol:
        return None
    clipped = np.clip(w, 0.0, 1.0)
    return clipped / clipped.sum(), residual, violation


def starting_points(
    n: int, extra: dict[str, np.ndarray], config: SolverConfig
) -> list[tuple[str, np.ndarray]]:
    starts = [("equal_weights", np.full(n, 1.0 / n))]
    starts += [(k, np.asarray(v, dtype=float)) for k, v in extra.items()]
    rng = np.random.default_rng(config.start_seed)
    starts += [
        (f"dirichlet_{i}", w) for i, w in enumerate(rng.dirichlet(np.ones(n), config.random_starts))
    ]
    return starts


def _run(
    objective: Callable[[np.ndarray], float],
    jac: Callable[[np.ndarray], np.ndarray],
    constraints: list[dict],
    starts: list[tuple[str, np.ndarray]],
    config: SolverConfig,
    accept: Callable[[np.ndarray], bool] = lambda w: True,
    bounds: list[tuple[float, float]] | None = None,
    transform: Callable[[np.ndarray], np.ndarray] | None = None,
) -> tuple[list[tuple[float, str, np.ndarray, int, float, float]], list[StartResult]]:
    n = len(starts[0][1])
    bounds = bounds or [(0.0, 1.0)] * n
    accepted, attempts = [], []
    for label, x0 in starts:
        res = minimize(
            objective,
            x0,
            jac=jac,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": config.ftol, "maxiter": config.maxiter},
        )
        w = transform(res.x) if transform is not None and np.isfinite(res.x).all() else res.x
        cleaned = _clean(w, config.weight_tolerance) if res.success else None
        ok = cleaned is not None and accept(cleaned[0])
        attempts.append(
            StartResult(
                label=label,
                success=bool(res.success),
                accepted=bool(ok),
                message=str(res.message),
                iterations=int(res.nit),
                evaluations=int(res.nfev),
                objective=float(res.fun) if np.isfinite(res.fun) else None,
            )
        )
        if ok:
            assert cleaned is not None
            accepted.append(
                (float(res.fun), label, cleaned[0], int(res.nit), cleaned[1], cleaned[2])
            )
    return accepted, attempts


_SUM_TO_ONE = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0, "jac": lambda w: np.ones_like(w)}


def _pick(
    accepted: list, attempts: list[StartResult], score: Callable[[np.ndarray], float], name: str
) -> tuple[np.ndarray, str, int, float, float, float]:
    if not accepted:
        raise SolverFailedError(f"{name}: no start converged to a feasible solution", attempts)
    best = min(accepted, key=lambda a: score(a[2]))
    _, label, w, nit, residual, violation = best
    return w, label, nit, residual, violation, score(w)


def minimize_volatility(
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free: float,
    *,
    extra_starts: dict[str, np.ndarray] | None = None,
    config: SolverConfig = DEFAULT_CONFIG,
) -> Solution:
    starts = starting_points(len(mu), extra_starts or {}, config)
    accepted, attempts = _run(
        lambda w: float(w @ cov @ w), lambda w: 2 * cov @ w, [_SUM_TO_ONE], starts, config
    )
    w, label, nit, res, viol, var = _pick(
        accepted, attempts, lambda w: float(w @ cov @ w), "minimum volatility"
    )
    ret, vol, sharpe = metrics(w, mu, cov, risk_free)
    best_vol_found = min(np.sqrt(max(float(a[2] @ cov @ a[2]), 0.0)) for a in accepted)
    return Solution(
        w,
        ret,
        vol,
        sharpe,
        var,
        label,
        nit,
        res,
        viol,
        attempts,
        verification={"start_spread_volatility": vol - best_vol_found},
    )


def maximize_sharpe(
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free: float,
    *,
    extra_starts: dict[str, np.ndarray] | None = None,
    config: SolverConfig = DEFAULT_CONFIG,
) -> Solution:
    excess = mu - risk_free
    if not (excess > 0).any():
        raise InfeasibleProblemError(
            "No asset has an expected return above the risk-free rate; the maximum-Sharpe "
            "portfolio is not defined in the usual sense",
            minimum_volatility=float("nan"),
        )

    def neg_sharpe(w: np.ndarray) -> float:
        var = float(w @ cov @ w)
        if var < MIN_VOLATILITY**2:
            return 1e6  # guard: undefined Sharpe at (near-)zero volatility
        return -float(w @ excess) / np.sqrt(var)

    def neg_sharpe_jac(w: np.ndarray) -> np.ndarray:
        var = float(w @ cov @ w)
        if var < MIN_VOLATILITY**2:
            return np.zeros_like(w)
        vol = np.sqrt(var)
        return -(excess / vol - float(w @ excess) * (cov @ w) / vol**3)

    def sharpe(w: np.ndarray) -> float:
        return -neg_sharpe(w)

    # 1) Convex rescaling: min y' S y  s.t. excess' y = 1, y >= 0;  w = y / sum(y).
    n = len(mu)
    y0 = np.where(excess > 0, 1.0, 0.0)
    y0 = y0 / float(y0 @ excess)
    convex, convex_attempts = _run(
        lambda y: float(y @ cov @ y),
        lambda y: 2 * cov @ y,
        [{"type": "eq", "fun": lambda y: float(y @ excess) - 1.0, "jac": lambda y: excess}],
        [("convex_rescaling", y0)],
        config,
        bounds=[(0.0, None)] * n,
        transform=lambda y: y / y.sum() if y.sum() > 0 else y,
    )
    # 2) Direct maximization from several feasible starts (incl. Monte Carlo candidate).
    starts = starting_points(n, extra_starts or {}, config)
    direct, direct_attempts = _run(neg_sharpe, neg_sharpe_jac, [_SUM_TO_ONE], starts, config)
    accepted = convex + direct
    attempts = convex_attempts + direct_attempts
    w, label, nit, res, viol, _ = _pick(accepted, attempts, lambda w: -sharpe(w), "maximum Sharpe")
    ret, vol, s = metrics(w, mu, cov, risk_free)
    verification = {}
    if convex:
        verification["convex_vs_direct_sharpe_gap"] = (
            abs(sharpe(convex[0][2]) - max(sharpe(a[2]) for a in direct))
            if direct
            else float("nan")
        )
    return Solution(
        w, ret, vol, s, -(s or 0.0), label, nit, res, viol, attempts, verification=verification
    )


def maximize_return(
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free: float,
    max_volatility: float,
    *,
    extra_starts: dict[str, np.ndarray] | None = None,
    config: SolverConfig = DEFAULT_CONFIG,
) -> Solution:
    if not np.isfinite(max_volatility) or max_volatility <= 0:
        raise OptimizationInputError("max_volatility must be a finite, positive number")
    floor = minimize_volatility(mu, cov, risk_free, config=config)
    if max_volatility < floor.volatility - config.volatility_tolerance:
        raise InfeasibleProblemError(
            f"No long-only portfolio has volatility at or below {max_volatility:.4%}: the "
            f"minimum achievable annualized volatility is {floor.volatility:.4%}",
            minimum_volatility=floor.volatility,
        )
    limit = max_volatility**2
    vol_constraint = {
        "type": "ineq",
        "fun": lambda w: limit - float(w @ cov @ w),
        "jac": lambda w: -2 * cov @ w,
    }
    starts = [
        ("minimum_volatility_solution", floor.weights),
        *starting_points(len(mu), extra_starts or {}, config),
    ]

    def within_limit(w: np.ndarray) -> bool:
        return (
            float(np.sqrt(max(float(w @ cov @ w), 0.0)))
            <= max_volatility + config.volatility_tolerance
        )

    accepted, attempts = _run(
        lambda w: -float(w @ mu),
        lambda w: -mu,
        [_SUM_TO_ONE, vol_constraint],
        starts,
        config,
        accept=within_limit,
    )
    w, label, nit, res, viol, neg_ret = _pick(
        accepted, attempts, lambda w: -float(w @ mu), "maximum return"
    )
    ret, vol, s = metrics(w, mu, cov, risk_free)
    return Solution(
        w,
        ret,
        vol,
        s,
        neg_ret,
        label,
        nit,
        res,
        viol,
        attempts,
        volatility_slack=max_volatility - vol,
    )


def efficient_frontier(
    mu: np.ndarray,
    cov: np.ndarray,
    risk_free: float,
    n_points: int = 30,
    *,
    config: SolverConfig = DEFAULT_CONFIG,
) -> list[tuple[float, float, np.ndarray]]:
    """Long-only efficient frontier: minimum variance at evenly spaced target returns
    from the minimum-volatility portfolio's return to max(mu). Warm-started; points
    whose solve fails the checks are omitted (never interpolated)."""
    if n_points < 2:
        raise OptimizationInputError("n_points must be at least 2")
    base = minimize_volatility(mu, cov, risk_free, config=config)
    targets = np.linspace(base.expected_return, float(mu.max()), n_points)
    out = [(base.expected_return, base.volatility, base.weights)]
    x0 = base.weights
    for target in targets[1:]:
        cons = [
            _SUM_TO_ONE,
            {"type": "eq", "fun": lambda w, t=target: float(w @ mu) - t, "jac": lambda w: mu},
        ]
        accepted, _ = _run(
            lambda w: float(w @ cov @ w), lambda w: 2 * cov @ w, cons, [("warm", x0)], config
        )
        if not accepted:
            corner = np.zeros_like(mu)
            corner[int(np.argmax(mu))] = 1.0
            accepted, _ = _run(
                lambda w: float(w @ cov @ w),
                lambda w: 2 * cov @ w,
                cons,
                [("corner", corner)],
                config,
            )
        if accepted:
            w = accepted[0][2]
            r, v, _ = metrics(w, mu, cov, risk_free)
            if abs(r - target) <= 1e-7:
                out.append((r, v, w))
                x0 = w
    return out
