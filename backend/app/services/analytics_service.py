"""Phase 3 descriptive analytics: orchestration, validation and caching.

Loads the validated Phase 2 dataset, calls the pure functions in ``app.analytics`` and
records every validation outcome. Results are cached per dataset version (the
manifest's ``generated_at``), so the API always reflects the current artifacts.
"""

import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics import ANALYTICS_VERSION
from app.analytics.conventions import Conventions
from app.analytics.covariance import (
    MatrixDiagnostics,
    annualize_covariance,
    correlation_matrix,
    covariance_matrix,
    diagnose,
    pairwise_observations,
)
from app.analytics.returns import max_return_discrepancy, returns_for, simple_returns
from app.analytics.risk_free import (
    RiskFreeProfile,
    UnsupportedYieldConventionError,
    profile_risk_free,
)
from app.analytics.statistics import DescriptiveStatistics, describe
from app.core.config import Settings
from app.core.errors import DataNotReadyError
from app.data.loader import RISK_FREE_ID, ProcessedDataLoader, ValidatedDataset
from app.data.validation import DatasetLoadError
from app.domain.assets import ASSET_IDS, BENCHMARK

RETURN_TOLERANCE = 1e-12
_SOURCE_KEYS = ("portfolio", "benchmark", "prices/", "risk_free/", "return_intervals")
RF_PROPOSED_CONVERSION = (
    "Per return interval (t-1, t]: use the latest auction yield with auction date <= t-1 "
    "(as-of join), accrued as rf_t = y/100 * calendar_days(t-1, t) / 365. Not applied in "
    "Phase 3; awaiting approval."
)


class AnalyticsStatus:
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # pass | warn | fail
    detail: str


@dataclass(frozen=True)
class AnalyticsResult:
    computed_at: datetime
    conventions: Conventions
    dataset: ValidatedDataset
    asset_returns: pd.DataFrame
    benchmark_returns: pd.DataFrame
    statistics_common: list[DescriptiveStatistics]
    statistics_individual: list[DescriptiveStatistics]
    correlation: pd.DataFrame
    covariance_daily: pd.DataFrame
    covariance_annualized: pd.DataFrame
    correlation_diagnostics: MatrixDiagnostics
    covariance_diagnostics: MatrixDiagnostics
    pairwise_counts: pd.DataFrame
    risk_free: RiskFreeProfile | None
    risk_free_error: str | None
    checks: list[Check] = field(default_factory=list)

    @property
    def status(self) -> str:
        statuses = {c.status for c in self.checks}
        if "fail" in statuses:
            return AnalyticsStatus.FAILED
        if "warn" in statuses:
            return AnalyticsStatus.PASS_WITH_WARNINGS
        return AnalyticsStatus.PASS

    @property
    def sample_start(self) -> str:
        return self.asset_returns.index[0].date().isoformat()

    @property
    def sample_end(self) -> str:
        return self.asset_returns.index[-1].date().isoformat()

    @property
    def multi_session_dates(self) -> list[str]:
        spans = self.dataset.sessions_spanned
        return [d.date().isoformat() for d in spans[spans > 1].index]

    def statistics(self, sample: str) -> list[DescriptiveStatistics]:
        return self.statistics_common if sample == "common" else self.statistics_individual


def compute_analytics(dataset: ValidatedDataset, conventions: Conventions) -> AnalyticsResult:
    checks: list[Check] = []
    prices, bench_prices = dataset.portfolio_prices, dataset.benchmark_prices
    bench = BENCHMARK.id

    if dataset.asset_ids != ASSET_IDS:
        raise DatasetLoadError(f"Asset columns {dataset.asset_ids} differ from the registry order")
    checks.append(Check("asset_order", "pass", "Columns follow the canonical registry order"))

    # Returns on the common sample, recomputed from aligned prices and cross-checked
    # against Phase 2's aligned return files.
    asset_returns = simple_returns(prices)
    bench_returns = simple_returns(bench_prices)
    diff = max(
        max_return_discrepancy(dataset.phase2_portfolio_returns, prices),
        max_return_discrepancy(dataset.phase2_benchmark_returns, bench_prices),
    )
    checks.append(
        Check(
            "returns_reproduce_phase2",
            "pass" if diff <= RETURN_TOLERANCE else "fail",
            f"Max |difference| vs Phase 2 aligned returns: {diff:.2e} "
            f"(tolerance {RETURN_TOLERANCE:.0e})",
        )
    )
    finite = bool(
        np.isfinite(asset_returns.to_numpy()).all() and np.isfinite(bench_returns.to_numpy()).all()
    )
    checks.append(
        Check(
            "returns_finite", "pass" if finite else "fail", "All common-sample returns are finite"
        )
    )
    multi = dataset.sessions_spanned[dataset.sessions_spanned > 1]
    if len(multi):
        checks.append(
            Check(
                "multi_session_returns",
                "warn",
                f"{len(multi)} of {len(asset_returns)} common-sample returns span more than one "
                "session (dates dropped in Phase 2 alignment); they are kept as single "
                "observations",
            )
        )

    # Descriptive statistics: common sample and each series' own validated history.
    common = [describe(a, asset_returns[a], prices[a], conventions) for a in ASSET_IDS]
    common.append(describe(bench, bench_returns[bench], bench_prices[bench], conventions))
    individual = []
    for ds_id in (*ASSET_IDS, bench):
        p = dataset.individual_prices[ds_id]
        r = returns_for(p, dataset.series_info[ds_id].value_kind)
        individual.append(describe(ds_id, r, p, conventions))
    unavailable = [
        s.series_id for s in common if s.annualized_return is None or s.std_daily is None
    ]
    checks.append(
        Check(
            "statistics_available",
            "fail" if unavailable else "pass",
            f"Unavailable statistics for {unavailable}"
            if unavailable
            else "All statistics estimable",
        )
    )

    # Dependence structure on the common sample only.
    n = len(asset_returns)
    corr = correlation_matrix(asset_returns)
    cov_d = covariance_matrix(asset_returns, conventions)
    cov_a = annualize_covariance(cov_d, conventions)
    corr_diag = diagnose(corr, n, kind="correlation", conventions=conventions)
    cov_diag = diagnose(cov_a, n, kind="covariance", conventions=conventions)
    pairs = pairwise_observations(asset_returns)
    for name, diag in (("correlation_matrix", corr_diag), ("covariance_matrix", cov_diag)):
        problems = diag.problems()
        checks.append(
            Check(
                name,
                "fail" if problems else "pass",
                "; ".join(problems)
                if problems
                else f"{len(diag.labels)}x{len(diag.labels)}, symmetric, finite, PSD "
                f"(min eigenvalue {diag.min_eigenvalue:.3e})",
            )
        )
    uniform = bool((pairs.to_numpy() == n).all())
    checks.append(
        Check(
            "common_sample",
            "pass" if uniform else "fail",
            f"Every pairwise estimate uses the same {n} dates"
            if uniform
            else "Pairwise sample sizes differ",
        )
    )

    # Risk-free series: inspection only.
    rf_profile, rf_error = None, None
    info = dataset.series_info[RISK_FREE_ID]
    try:
        rf_profile = profile_risk_free(
            dataset.risk_free,
            series_id=RISK_FREE_ID,
            units=info.units,
            study_start=prices.index[0],
            proposed_conversion=RF_PROPOSED_CONVERSION,
            limitations=(
                "Weekly primary-auction yields, not daily secondary-market yields.",
                "No daily risk-free series is derived in Phase 3; the conversion awaits approval.",
            ),
        )
        checks.append(
            Check(
                "risk_free_conversion",
                "warn",
                f"{rf_profile.frequency} {rf_profile.units} series inspected; "
                "daily conversion pending approval",
            )
        )
    except UnsupportedYieldConventionError as exc:
        rf_error = str(exc)
        checks.append(Check("risk_free_conversion", "fail", rf_error))

    if dataset.overall_status != "PASS":
        checks.append(
            Check(
                "upstream_data_quality",
                "warn",
                f"Phase 2 dataset status {dataset.overall_status} with "
                f"{len(dataset.warnings)} warning(s)",
            )
        )

    return AnalyticsResult(
        computed_at=datetime.now(UTC).replace(microsecond=0),
        conventions=conventions,
        dataset=dataset,
        asset_returns=asset_returns,
        benchmark_returns=bench_returns,
        statistics_common=common,
        statistics_individual=individual,
        correlation=corr,
        covariance_daily=cov_d,
        covariance_annualized=cov_a,
        correlation_diagnostics=corr_diag,
        covariance_diagnostics=cov_diag,
        pairwise_counts=pairs,
        risk_free=rf_profile,
        risk_free_error=rf_error,
        checks=checks,
    )


# ------------------------------------------------------------------------------ cache

_cache: dict[tuple[str, str], AnalyticsResult] = {}
_lock = threading.Lock()


class AnalyticsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._conventions = Conventions(
            periods_per_year=settings.trading_days_per_year,
            min_annualization_days=settings.analytics_min_annualization_days,
        )

    def result(self) -> AnalyticsResult:
        """Compute (or reuse) analytics for the current validated dataset."""
        loader = ProcessedDataLoader(self._settings.data_dir)
        try:
            dataset = loader.load()
        except DatasetLoadError as exc:
            raise DataNotReadyError(str(exc), details={"stage": "load", "path": exc.path}) from exc
        key = (str(self._settings.data_dir), dataset.manifest_generated_at)
        with _lock:
            cached = _cache.get(key)
            if cached is None or cached.conventions != self._conventions:
                try:
                    cached = compute_analytics(dataset, self._conventions)
                except (DatasetLoadError, ValueError) as exc:
                    raise DataNotReadyError(
                        f"Descriptive analytics could not be computed: {exc}",
                        details={"stage": "compute"},
                    ) from exc
                _cache[key] = cached
        return cached


def clear_cache() -> None:
    with _lock:
        _cache.clear()


# ------------------------------------------------------------------- serialization


def statistics_frame(stats: list[DescriptiveStatistics], sample: str) -> pd.DataFrame:
    rows = []
    for s in stats:
        row = asdict(s)
        row["notes"] = "; ".join(s.notes)
        row["sample"] = sample
        rows.append(row)
    return pd.DataFrame(rows)


def summary_document(result: AnalyticsResult, files: dict[str, str]) -> dict[str, Any]:
    ds, c = result.dataset, result.conventions
    return {
        "analytics_version": ANALYTICS_VERSION,
        "computed_at": result.computed_at.isoformat(),
        "status": result.status,
        "checks": [asdict(x) for x in result.checks],
        "source_dataset": {
            "note": "Phase 2 artifacts (source metadata); not modified by Phase 3",
            "manifest_generated_at": ds.manifest_generated_at,
            "pipeline_version": ds.pipeline_version,
            "overall_status": ds.overall_status,
            "files": {
                k: v
                for k, v in ds.source_files.items()
                if k.startswith(
                    ("portfolio", "benchmark", "prices/", "risk_free/", "return_intervals")
                )
            },
        },
        "sample": {
            "assets": list(ASSET_IDS),
            "benchmark": BENCHMARK.id,
            "price_start": ds.portfolio_prices.index[0].date().isoformat(),
            "start": result.sample_start,
            "end": result.sample_end,
            "return_observations": len(result.asset_returns),
            "multi_session_returns": result.multi_session_dates,
            "individual_samples": {
                s.series_id: {"start": s.start, "end": s.end, "observations": s.observations}
                for s in result.statistics_individual
            },
        },
        "conventions": c.describe(),
        "missing_data_policy": "Statistics and matrices use the Phase 2 common sample (inner join, "
        "no filling). Individual-sample statistics use each series' own validated dates and are "
        "descriptive only. No missing value is replaced; returns spanning dropped sessions "
        "are kept.",
        "matrix_diagnostics": {
            "correlation": asdict(result.correlation_diagnostics),
            "covariance_annualized": asdict(result.covariance_diagnostics),
        },
        "risk_free": asdict(result.risk_free)
        if result.risk_free
        else {"error": result.risk_free_error},
        "outputs": files,
        "disclaimer": "Historical, descriptive statistics only; they do not forecast future "
        "returns or risk.",
    }


def persist(result: AnalyticsResult, data_dir: Path) -> dict[str, str]:
    """Write Phase 3 outputs next to (never over) the Phase 2 artifacts."""
    from app.services.analytics_outputs import write_analytics_outputs

    return write_analytics_outputs(result, data_dir)
