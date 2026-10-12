"""Monte Carlo portfolio simulation (Phase 5): orchestration, checks, persistence."""

import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.analytics.covariance import diagnose
from app.analytics.efficient_frontier import FRONTIER_TOLERANCE, LABEL, non_dominated
from app.analytics.monte_carlo import (
    SimulationConfig,
    SimulationInputError,
    SimulationResult,
    dirichlet_weights,
    distribution_summary,
    simulate,
)
from app.core.config import Settings
from app.core.errors import DataNotReadyError, InvalidParameterError
from app.schemas.portfolio import (
    AssetWeight,
    CandidatePortfolio,
    Distribution,
    PointSet,
    SimulationCheck,
    SimulationInputs,
    SimulationRequest,
    SimulationResponse,
    SimulationSummary,
)
from app.services.market_inputs import (
    EXPECTED_RETURN_CONVENTION,
    RISK_FREE_CONVENTION,
    MarketInputs,
    market_inputs,
)

METHOD = (
    "Symmetric Dirichlet(alpha=1) weights, i.e. uniform on the long-only simplex "
    "(0 <= w_i <= 1, sum w_i = 1); numpy.random.default_rng(seed)"
)
FRONTIER_CRITERION = (
    "Keep a sampled portfolio if no other sampled portfolio has volatility <= and return >= "
    f"with one strict inequality (return tolerance {FRONTIER_TOLERANCE:g})"
)
_CACHE_SIZE = 8
_cache: "OrderedDict[tuple[str, str, int, int], SimulationResult]" = OrderedDict()
_lock = threading.Lock()


@dataclass(frozen=True)
class SimulationRun:
    inputs: MarketInputs
    result: SimulationResult
    checks: list[SimulationCheck]
    files: dict[str, str]

    @property
    def simulation_id(self) -> str:
        c = self.result.config
        return f"mc_n{c.n_portfolios}_seed{c.seed}"


def _checks(inputs: MarketInputs, res: SimulationResult) -> list[SimulationCheck]:
    out = []
    w = res.weights
    out.append(
        SimulationCheck(
            name="weights_valid",
            status="pass",
            detail=f"{w.shape[0]:,} x {w.shape[1]} weights in [0, 1]; max |sum - 1| = "
            f"{np.abs(w.sum(axis=1) - 1).max():.1e}",
        )
    )
    out.append(
        SimulationCheck(
            name="asset_order",
            status="pass" if list(res.asset_ids) == list(inputs.covariance.index) else "fail",
            detail="Weights, expected returns and covariance share the canonical order",
        )
    )
    diag = diagnose(inputs.covariance, len(inputs.analytics.asset_returns), kind="covariance")
    out.append(
        SimulationCheck(
            name="covariance_psd",
            status="pass" if diag.valid else "fail",
            detail="Annualized covariance symmetric and PSD "
            f"(min eigenvalue {diag.min_eigenvalue:.3e})",
        )
    )
    again = dirichlet_weights(w.shape[0], w.shape[1], res.config.seed, res.config.dirichlet_alpha)
    out.append(
        SimulationCheck(
            name="seed_reproducible",
            status="pass" if np.array_equal(again, w) else "fail",
            detail=f"Re-drawing with seed {res.config.seed} reproduces every weight exactly",
        )
    )
    mu = inputs.expected_returns.to_numpy()
    cov = inputs.covariance.to_numpy()
    worst = 0.0
    for i in {res.min_volatility_index, res.max_sharpe_index or 0}:
        wi = w[i]
        ret = sum(wi[k] * mu[k] for k in range(len(mu)))
        var = sum(wi[a] * cov[a, b] * wi[b] for a in range(len(mu)) for b in range(len(mu)))
        worst = max(worst, abs(ret - res.expected_returns[i]), abs(var**0.5 - res.volatilities[i]))
    out.append(
        SimulationCheck(
            name="independent_recalculation",
            status="pass" if worst < 1e-12 else "fail",
            detail="Candidate return/volatility recomputed with explicit sums: "
            f"max diff {worst:.1e}",
        )
    )
    undefined = int((~res.sharpe_defined).sum())
    out.append(
        SimulationCheck(
            name="sharpe_defined",
            status="pass" if undefined == 0 else "warn",
            detail=f"{undefined} portfolio(s) below the volatility floor have no Sharpe ratio",
        )
    )
    return out


def _persist(
    run_id: str, inputs: MarketInputs, res: SimulationResult, directory: Path, root: Path
) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    data_path = directory / f"{run_id}.csv.gz"
    meta_path = directory / f"{run_id}.json"
    dataset_ts = inputs.analytics.dataset.manifest_generated_at
    current = None
    if meta_path.is_file():
        try:
            current = json.loads(meta_path.read_text(encoding="utf-8")).get("dataset_generated_at")
        except (OSError, ValueError):
            current = None
    if current != dataset_ts or not data_path.is_file():
        res.frame().to_csv(data_path, index=False, compression="gzip", lineterminator="\n")
        meta = {
            "simulation_id": run_id,
            "n_portfolios": res.config.n_portfolios,
            "seed": res.config.seed,
            "dirichlet_alpha": res.config.dirichlet_alpha,
            "method": METHOD,
            "asset_order": list(res.asset_ids),
            "expected_returns": inputs.expected_returns.to_dict(),
            "expected_return_convention": EXPECTED_RETURN_CONVENTION,
            "covariance": inputs.covariance.to_numpy().tolist(),
            "risk_free_rate": res.risk_free,
            "risk_free_convention": RISK_FREE_CONVENTION,
            "dataset_generated_at": dataset_ts,
            "sample": {
                "start": inputs.analytics.sample_start,
                "end": inputs.analytics.sample_end,
                "observations": len(inputs.analytics.asset_returns),
            },
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {
        "portfolios": data_path.relative_to(root).as_posix(),
        "metadata": meta_path.relative_to(root).as_posix(),
    }


def run(settings: Settings, request: SimulationRequest) -> SimulationRun:
    if request.n_portfolios > settings.max_monte_carlo_simulations:
        raise InvalidParameterError(
            f"n_portfolios exceeds the configured maximum {settings.max_monte_carlo_simulations}"
        )
    inputs = market_inputs(settings)
    config = SimulationConfig(
        n_portfolios=request.n_portfolios,
        seed=request.seed,
        max_portfolios=settings.max_monte_carlo_simulations,
    )
    key = (
        str(settings.data_dir),
        inputs.analytics.dataset.manifest_generated_at,
        config.n_portfolios,
        config.seed,
    )
    with _lock:
        res = _cache.get(key)
    if res is None:
        try:
            res = simulate(
                inputs.expected_returns, inputs.covariance, inputs.risk_free_annual, config
            )
        except SimulationInputError as exc:
            raise DataNotReadyError(
                f"Simulation inputs are invalid: {exc}", details={"stage": "simulation"}
            ) from exc
        with _lock:
            _cache[key] = res
            while len(_cache) > _CACHE_SIZE:
                _cache.popitem(last=False)
    checks = _checks(inputs, res)
    run_id = f"mc_n{config.n_portfolios}_seed{config.seed}"
    files = _persist(
        run_id, inputs, res, settings.processed_dir / "simulations", settings.data_dir.parent
    )
    return SimulationRun(inputs=inputs, result=res, checks=checks, files=files)


def _points(res: SimulationResult, idx: np.ndarray) -> PointSet:
    sharpe = res.sharpe[idx]
    return PointSet(
        portfolio_ids=idx.tolist(),
        expected_returns=res.expected_returns[idx].tolist(),
        volatilities=res.volatilities[idx].tolist(),
        sharpe_ratios=[float(x) if np.isfinite(x) else None for x in sharpe],
    )


def _candidate(res: SimulationResult, label: str, i: int) -> CandidatePortfolio:
    s = res.sharpe[i]
    return CandidatePortfolio(
        label=label,
        portfolio_id=i,
        weights=[
            AssetWeight(asset_id=a, weight=float(w))
            for a, w in zip(res.asset_ids, res.weights[i], strict=True)
        ],
        expected_return=float(res.expected_returns[i]),
        volatility=float(res.volatilities[i]),
        sharpe_ratio=float(s) if np.isfinite(s) else None,
    )


def to_response(run_: SimulationRun, scatter_points: int) -> SimulationResponse:
    res, inputs = run_.result, run_.inputs
    candidates = [_candidate(res, "min_volatility", res.min_volatility_index)]
    if res.max_sharpe_index is not None:
        candidates.append(_candidate(res, "max_sharpe", res.max_sharpe_index))
    n_scatter = min(scatter_points, res.config.n_portfolios)
    statuses = {c.status for c in run_.checks}
    warnings = [
        "Candidates are the best of a finite random sample, not guaranteed global optima; "
        "Phase 6 constrained optimization will refine them.",
        "Uniform Dirichlet sampling rarely produces corner or concentrated portfolios, where "
        "optima often lie.",
        "Expected returns are historical arithmetic means; they are noisy estimates, not "
        "forecasts, and dominate the location of high-Sharpe portfolios.",
        "Covariance is the historical sample estimate on the common sample (no shrinkage).",
        f"Sharpe ratios use R_f = {res.risk_free:.2%} (see risk-free convention); the "
        "risk-free conversion awaits formal approval.",
    ]
    return SimulationResponse(
        status="FAILED" if "fail" in statuses else "PASS_WITH_WARNINGS",
        simulation_id=run_.simulation_id,
        n_portfolios=res.config.n_portfolios,
        seed=res.config.seed,
        method=METHOD,
        inputs=SimulationInputs(
            asset_order=list(res.asset_ids),
            expected_returns={k: float(v) for k, v in inputs.expected_returns.items()},
            expected_return_convention=EXPECTED_RETURN_CONVENTION,
            covariance_convention="Annualized sample covariance (daily x periods_per_year) "
            "on the common sample",
            risk_free_rate=res.risk_free,
            risk_free_convention=RISK_FREE_CONVENTION,
            sample_start=inputs.analytics.sample_start,
            sample_end=inputs.analytics.sample_end,
            observations=len(inputs.analytics.asset_returns),
            dataset_generated_at=inputs.analytics.dataset.manifest_generated_at,
        ),
        summary=SimulationSummary(
            expected_return=Distribution(**distribution_summary(res.expected_returns)),
            volatility=Distribution(**distribution_summary(res.volatilities)),
            sharpe_ratio=Distribution(**distribution_summary(res.sharpe)),
            sharpe_undefined=int((~res.sharpe_defined).sum()),
        ),
        candidates=candidates,
        scatter=_points(res, np.arange(n_scatter)),
        scatter_selection=f"Portfolios 0..{n_scatter - 1} (the first draws; draws are i.i.d., "
        "so this is a deterministic unbiased subsample). All portfolios are in the persisted file.",
        frontier=_points(res, non_dominated(res.expected_returns, res.volatilities)),
        frontier_label=LABEL,
        frontier_criterion=FRONTIER_CRITERION,
        checks=run_.checks,
        warnings=warnings,
        output_files=run_.files,
    )


def clear_cache() -> None:
    with _lock:
        _cache.clear()
