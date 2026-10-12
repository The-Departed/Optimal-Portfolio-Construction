"""Constrained optimization for the three investor profiles (Phase 6).

Uses exactly the Monte Carlo inputs (``market_inputs``: mu, Sigma, R_f), so the
optimizer-versus-simulation comparison is made under identical assumptions.
"""

import numpy as np

from app.analytics import optimization as opt
from app.core.config import Settings
from app.core.errors import (
    DataNotReadyError,
    InfeasibleConstraintError,
    InvalidParameterError,
    OptimizationFailedError,
)
from app.domain.profiles import PROFILE_DEFINITIONS, InvestorProfile
from app.schemas.portfolio import (
    AssetWeight,
    CandidatePortfolio,
    ConstraintCheck,
    EstimationInputs,
    FrontierPoint,
    FrontierResponse,
    OptimizationRequest,
    OptimizationResponse,
    OptimizedPortfolio,
    SimulationComparison,
    SimulationRequest,
    SolverAttempt,
    SolverDiagnostics,
)
from app.services import simulation_service
from app.services.market_inputs import (
    EXPECTED_RETURN_CONVENTION,
    RISK_FREE_CONVENTION,
    MarketInputs,
    market_inputs,
)

CONFIG = opt.DEFAULT_CONFIG
COVARIANCE_CONVENTION = (
    "Annualized sample covariance (daily x periods_per_year, ddof = 1) on the Phase 3 "
    "common sample; validated symmetric and positive semidefinite, never adjusted"
)
LIMITATIONS = [
    "Weights are optimal for historical estimates of mu and Sigma; small changes in "
    "expected returns can change the allocation substantially (estimation error).",
    "Expected returns are historical arithmetic means, not forecasts; covariance is the "
    "unshrunk sample estimate.",
    "Sharpe ratios use the adopted risk-free convention (formal approval pending). No "
    "transaction costs, taxes, liquidity limits or rebalancing are modelled.",
]


def _inputs(inputs: MarketInputs) -> EstimationInputs:
    a = inputs.analytics
    return EstimationInputs(
        asset_order=list(inputs.expected_returns.index),
        expected_returns={k: float(v) for k, v in inputs.expected_returns.items()},
        expected_return_convention=EXPECTED_RETURN_CONVENTION,
        covariance_convention=COVARIANCE_CONVENTION,
        risk_free_rate=inputs.risk_free_annual,
        risk_free_convention=RISK_FREE_CONVENTION,
        sample_start=a.sample_start,
        sample_end=a.sample_end,
        observations=len(a.asset_returns),
        dataset_generated_at=a.dataset.manifest_generated_at,
    )


def _weights(labels: list[str], w: np.ndarray) -> list[AssetWeight]:
    return [AssetWeight(asset_id=a, weight=float(x)) for a, x in zip(labels, w, strict=True)]


def _arrays(inputs: MarketInputs) -> tuple[np.ndarray, np.ndarray, float, list[str]]:
    labels = list(inputs.expected_returns.index)
    mu = inputs.expected_returns.to_numpy(dtype="float64")
    cov = inputs.covariance.to_numpy(dtype="float64")
    try:
        opt.validate_inputs(mu, cov, inputs.risk_free_annual, labels)
    except opt.OptimizationInputError as exc:
        raise DataNotReadyError(
            f"Optimization inputs are invalid: {exc}", details={"stage": "optimization_inputs"}
        ) from exc
    return mu, cov, inputs.risk_free_annual, labels


def _comparison(
    profile: InvestorProfile,
    sol: opt.Solution,
    run: simulation_service.SimulationRun,
    max_volatility: float | None,
    passes: bool,
) -> SimulationComparison:
    res = run.result
    if profile is InvestorProfile.CONSERVATIVE:
        idx, rule = res.min_volatility_index, "lowest-volatility simulated portfolio"
    elif profile is InvestorProfile.BALANCED:
        idx, rule = res.max_sharpe_index, "highest-Sharpe simulated portfolio"
    else:
        assert max_volatility is not None
        ok = np.flatnonzero(res.volatilities <= max_volatility)
        idx = int(ok[np.argmax(res.expected_returns[ok])]) if len(ok) else None
        rule = f"highest-return simulated portfolio with volatility <= {max_volatility:.2%}"
    base = {
        "simulation_id": run.simulation_id,
        "n_portfolios": res.config.n_portfolios,
        "seed": res.config.seed,
        "candidate_rule": rule,
        "optimizer_passes_checks": passes,
    }
    if idx is None:
        return SimulationComparison(
            **base,
            candidate=None,
            candidate_satisfies_constraints=None,
            return_difference=None,
            volatility_difference=None,
            sharpe_difference=None,
            note="No simulated portfolio satisfies the requested volatility limit.",
        )
    s = res.sharpe[idx]
    cand = CandidatePortfolio(
        label=profile.value,
        portfolio_id=int(idx),
        weights=_weights(list(res.asset_ids), res.weights[idx]),
        expected_return=float(res.expected_returns[idx]),
        volatility=float(res.volatilities[idx]),
        sharpe_ratio=float(s) if np.isfinite(s) else None,
    )
    w = res.weights[idx]
    satisfies = bool(abs(w.sum() - 1) <= CONFIG.weight_tolerance and w.min() >= 0 and w.max() <= 1)
    if max_volatility is not None:
        satisfies = satisfies and cand.volatility <= max_volatility
    return SimulationComparison(
        **base,
        candidate=cand,
        candidate_satisfies_constraints=satisfies,
        return_difference=sol.expected_return - cand.expected_return,
        volatility_difference=sol.volatility - cand.volatility,
        sharpe_difference=(sol.sharpe - cand.sharpe_ratio)
        if sol.sharpe is not None and cand.sharpe_ratio is not None
        else None,
        note="Same mu, Sigma, R_f and long-only constraints for both methods; the simulated "
        "candidate is the best of a finite random sample.",
    )


def _not_worse(
    profile: InvestorProfile, sol: opt.Solution, comp: SimulationComparison
) -> list[str]:
    """A converged convex solution should never be beaten by a sampled portfolio."""
    c = comp.candidate
    if c is None:
        return []
    tol = 1e-9
    worse = (
        (profile is InvestorProfile.CONSERVATIVE and sol.volatility > c.volatility + tol)
        or (
            profile is InvestorProfile.BALANCED
            and sol.sharpe is not None
            and c.sharpe_ratio is not None
            and sol.sharpe < c.sharpe_ratio - tol
        )
        or (profile is InvestorProfile.GROWTH and sol.expected_return < c.expected_return - tol)
    )
    return (
        [
            "The simulated candidate outperforms the optimizer: treat the optimizer result "
            "with caution."
        ]
        if worse
        else []
    )


def optimize(settings: Settings, request: OptimizationRequest) -> OptimizationResponse:
    profile = request.profile
    run = simulation_service.run(
        settings,
        SimulationRequest(n_portfolios=request.simulation_portfolios, seed=request.simulation_seed),
    )
    inputs = run.inputs
    mu, cov, rf, labels = _arrays(inputs)
    res = run.result
    extra: dict[str, np.ndarray] = {}
    try:
        if profile is InvestorProfile.CONSERVATIVE:
            extra["monte_carlo_min_volatility"] = res.weights[res.min_volatility_index]
            sol = opt.minimize_volatility(mu, cov, rf, extra_starts=extra, config=CONFIG)
        elif profile is InvestorProfile.BALANCED:
            if res.max_sharpe_index is not None:
                extra["monte_carlo_max_sharpe"] = res.weights[res.max_sharpe_index]
            sol = opt.maximize_sharpe(mu, cov, rf, extra_starts=extra, config=CONFIG)
        else:
            assert request.max_volatility is not None
            feasible = np.flatnonzero(res.volatilities <= request.max_volatility)
            if len(feasible):
                best = feasible[np.argmax(res.expected_returns[feasible])]
                extra["monte_carlo_best_within_limit"] = res.weights[best]
            sol = opt.maximize_return(
                mu, cov, rf, request.max_volatility, extra_starts=extra, config=CONFIG
            )
    except opt.OptimizationInputError as exc:
        raise InvalidParameterError(str(exc)) from exc
    except opt.InfeasibleProblemError as exc:
        raise InfeasibleConstraintError(
            str(exc),
            details={
                "minimum_volatility": exc.minimum_volatility,
                "requested_max_volatility": request.max_volatility,
            },
        ) from exc
    except opt.SolverFailedError as exc:
        raise OptimizationFailedError(
            f"The optimizer did not converge to a feasible portfolio: {exc}",
            details={"attempts": [a.message for a in exc.attempts]},
        ) from exc

    w = sol.weights
    vol_ok = (
        sol.volatility <= request.max_volatility + CONFIG.volatility_tolerance
        if request.max_volatility is not None
        else True
    )
    feasible = bool(
        abs(w.sum() - 1) <= CONFIG.weight_tolerance and w.min() >= 0 and w.max() <= 1 and vol_ok
    )
    if not feasible:  # defensive: _clean already enforces this
        raise OptimizationFailedError("The optimized weights failed the final feasibility checks")
    comparison = _comparison(profile, sol, run, request.max_volatility, feasible)
    definition = PROFILE_DEFINITIONS[profile]
    accepted = [a for a in sol.attempts if a.accepted]
    warnings = [*_not_worse(profile, sol, comparison), *LIMITATIONS]
    binding = (
        sol.volatility_slack is not None and sol.volatility_slack <= CONFIG.volatility_tolerance
    )
    if profile is InvestorProfile.GROWTH and binding:
        warnings.insert(0, "The volatility limit is binding: the portfolio sits on the limit.")
    return OptimizationResponse(
        profile=profile,
        label=definition.label,
        objective=definition.objective,
        formulation=definition.formulation,
        status="optimal",
        max_volatility=request.max_volatility,
        portfolio=OptimizedPortfolio(
            weights=_weights(labels, w),
            expected_return=sol.expected_return,
            volatility=sol.volatility,
            sharpe_ratio=sol.sharpe,
        ),
        inputs=_inputs(inputs),
        solver=SolverDiagnostics(
            solver=opt.SOLVER,
            configuration=CONFIG.describe(),
            success=True,
            convex_problem=True,
            best_start=sol.best_start,
            iterations=sol.iterations,
            starts_tried=len(sol.attempts),
            starts_accepted=len(accepted),
            attempts=[
                SolverAttempt(
                    label=a.label,
                    success=a.success,
                    accepted=a.accepted,
                    message=a.message,
                    iterations=a.iterations,
                    evaluations=a.evaluations,
                )
                for a in sol.attempts
            ],
            verification={k: float(v) for k, v in sol.verification.items()},
        ),
        constraints=ConstraintCheck(
            sum_of_weights=float(w.sum()),
            sum_residual_raw=sol.sum_residual,
            bound_violation_raw=sol.bound_violation,
            min_weight=float(w.min()),
            max_weight=float(w.max()),
            volatility_limit=request.max_volatility,
            volatility_slack=sol.volatility_slack,
            tolerance={
                "weights": CONFIG.weight_tolerance,
                "volatility": CONFIG.volatility_tolerance,
            },
            feasible=feasible,
        ),
        comparison=comparison,
        warnings=warnings,
    )


def frontier(settings: Settings, points: int) -> FrontierResponse:
    inputs = market_inputs(settings)
    mu, cov, rf, labels = _arrays(inputs)
    pts = opt.efficient_frontier(mu, cov, rf, points, config=CONFIG)
    return FrontierResponse(
        label="Long-only efficient frontier (constrained minimum variance at target returns)",
        method=f"{opt.SOLVER}: minimize w' Sigma w s.t. w' mu = target, sum(w) = 1, "
        "0 <= w_i <= 1, for evenly spaced targets from the minimum-volatility return to max(mu)",
        asset_order=labels,
        risk_free_rate=rf,
        points=[
            FrontierPoint(
                expected_return=r,
                volatility=v,
                sharpe_ratio=(r - rf) / v if v > 0 else None,
                weights=[float(x) for x in w],
            )
            for r, v, w in pts
        ],
    )
