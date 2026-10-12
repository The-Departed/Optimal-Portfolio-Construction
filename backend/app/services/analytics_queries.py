"""Maps cached analytics results to API response schemas (no calculations)."""

from dataclasses import asdict

import pandas as pd

from app.analytics.covariance import MatrixDiagnostics, diagnose
from app.analytics.returns import simple_returns
from app.analytics.statistics import histogram
from app.core.errors import InvalidParameterError
from app.domain.assets import ASSET_IDS, BENCHMARK, get_asset
from app.schemas.analytics import (
    AnalyticsCheck,
    AnalyticsSummaryResponse,
    CovarianceFrequency,
    DistributionResponse,
    MatrixDiagnosticsOut,
    MatrixResponse,
    ReturnsResponse,
    RiskFreeObservation,
    RiskFreeProfileOut,
    RiskFreeResponse,
    Sample,
    SampleInfo,
    SeriesStatistics,
    StatisticsResponse,
)
from app.services.analytics_service import AnalyticsResult

ALL_SERIES = (*ASSET_IDS, BENCHMARK.id)


def resolve_series(requested: list[str] | None, *, allow_benchmark: bool = True) -> list[str]:
    allowed = ALL_SERIES if allow_benchmark else ASSET_IDS
    if not requested:
        return list(allowed)
    ids = [s.strip().upper() for item in requested for s in item.split(",") if s.strip()]
    unknown = [s for s in ids if s not in allowed]
    if unknown:
        raise InvalidParameterError(
            f"Unknown series {unknown}; valid identifiers: {list(allowed)}",
            details={"unknown": unknown, "valid": list(allowed)},
        )
    return [s for s in allowed if s in ids]  # canonical order, de-duplicated


def single_series(requested: str) -> str:
    ids = resolve_series([requested])
    if len(ids) != 1:
        raise InvalidParameterError("Exactly one series identifier is required")
    return ids[0]


def _name(series_id: str) -> tuple[str, str]:
    if series_id == BENCHMARK.id:
        return BENCHMARK.name, "benchmark"
    return get_asset(series_id).name, "portfolio_asset"


def summary(result: AnalyticsResult) -> AnalyticsSummaryResponse:
    ds = result.dataset
    return AnalyticsSummaryResponse(
        status=result.status,
        analytics_version=_version(),
        computed_at=result.computed_at.isoformat(),
        dataset_generated_at=ds.manifest_generated_at,
        dataset_status=ds.overall_status,
        sample=SampleInfo(
            start=result.sample_start,
            end=result.sample_end,
            price_start=ds.portfolio_prices.index[0].date().isoformat(),
            observations=len(result.asset_returns),
            multi_session_returns=len(result.multi_session_dates),
        ),
        assets=list(ASSET_IDS),
        benchmark=BENCHMARK.id,
        checks=[AnalyticsCheck(**asdict(c)) for c in result.checks],
        conventions=result.conventions.describe(),
        risk_free=RiskFreeProfileOut(**asdict(result.risk_free)) if result.risk_free else None,
        upstream_warnings=list(ds.warnings),
        disclaimer="Historical, descriptive statistics only; they do not forecast future "
        "returns or risk, and low historical correlation does not guarantee future "
        "diversification.",
    )


def _version() -> str:
    from app.analytics import ANALYTICS_VERSION

    return ANALYTICS_VERSION


def statistics(result: AnalyticsResult, sample: Sample, series: list[str]) -> StatisticsResponse:
    rows = []
    for s in result.statistics(sample.value):
        if s.series_id not in series:
            continue
        name, role = _name(s.series_id)
        data = asdict(s)
        data["notes"] = list(s.notes)
        rows.append(SeriesStatistics(name=name, role=role, **data))
    return StatisticsResponse(
        sample=sample,
        periods_per_year=result.conventions.periods_per_year,
        calendar_days_per_year=result.conventions.calendar_days_per_year,
        series=rows,
    )


def _diag(d: MatrixDiagnostics) -> MatrixDiagnosticsOut:
    return MatrixDiagnosticsOut(
        symmetric=d.symmetric,
        max_asymmetry=d.max_asymmetry,
        finite=d.finite,
        positive_semidefinite=d.positive_semidefinite,
        min_eigenvalue=d.min_eigenvalue,
        max_eigenvalue=d.max_eigenvalue,
        condition_number=d.condition_number,
        valid=d.valid,
        problems=d.problems(),
    )


def _matrix(
    result: AnalyticsResult,
    m: pd.DataFrame,
    kind: str,
    diag: MatrixDiagnostics,
    frequency: CovarianceFrequency | None,
) -> MatrixResponse:
    return MatrixResponse(
        kind=kind,
        frequency=frequency,
        labels=list(m.index),
        values=m.to_numpy().tolist(),
        observations=diag.observations,
        pairwise_observations=result.pairwise_counts.to_numpy().tolist(),
        start=result.sample_start,
        end=result.sample_end,
        diagnostics=_diag(diag),
    )


def correlation(result: AnalyticsResult) -> MatrixResponse:
    return _matrix(result, result.correlation, "correlation", result.correlation_diagnostics, None)


def covariance(result: AnalyticsResult, frequency: CovarianceFrequency) -> MatrixResponse:
    if frequency is CovarianceFrequency.DAILY:
        m = result.covariance_daily
        diag = diagnose(
            m, len(result.asset_returns), kind="covariance", conventions=result.conventions
        )
    else:
        m, diag = result.covariance_annualized, result.covariance_diagnostics
    return _matrix(result, m, "covariance", diag, frequency)


def returns(
    result: AnalyticsResult, series: list[str], start: str | None, end: str | None
) -> ReturnsResponse:
    table = pd.concat([result.asset_returns, result.benchmark_returns], axis=1)[series]
    spans = result.dataset.sessions_spanned
    try:
        lo = pd.Timestamp(start) if start else table.index[0]
        hi = pd.Timestamp(end) if end else table.index[-1]
    except ValueError as exc:
        raise InvalidParameterError(f"Invalid date: {exc}") from exc
    if lo > hi:
        raise InvalidParameterError("start must not be after end")
    window = table.loc[lo:hi]
    if window.empty:
        raise InvalidParameterError(
            f"No observations between {lo.date()} and {hi.date()}; sample is "
            f"{result.sample_start} .. {result.sample_end}"
        )
    return ReturnsResponse(
        start=window.index[0].date().isoformat(),
        end=window.index[-1].date().isoformat(),
        observations=len(window),
        series_ids=series,
        dates=[d.date().isoformat() for d in window.index],
        returns={c: window[c].tolist() for c in window.columns},
        sessions_spanned=spans.loc[window.index].astype(int).tolist(),
    )


def distribution(
    result: AnalyticsResult, series_id: str, sample: Sample, bins: int
) -> DistributionResponse:
    if sample is Sample.COMMON:
        r = pd.concat([result.asset_returns, result.benchmark_returns], axis=1)[series_id]
    else:
        r = simple_returns(result.dataset.individual_prices[series_id])
    counts, edges = histogram(r, bins)
    stats = next(s for s in result.statistics(sample.value) if s.series_id == series_id)
    return DistributionResponse(
        series_id=series_id,
        sample=sample,
        observations=len(r),
        bin_edges=edges.tolist(),
        counts=counts.astype(int).tolist(),
        mean_daily=stats.mean_daily,
        std_daily=stats.std_daily,
    )


def risk_free(result: AnalyticsResult) -> RiskFreeResponse:
    rf = result.dataset.risk_free
    return RiskFreeResponse(
        profile=RiskFreeProfileOut(**asdict(result.risk_free)) if result.risk_free else None,
        error=result.risk_free_error,
        observations=[
            RiskFreeObservation(
                auction_date=d.date().isoformat(),
                implicit_yield_pct=float(y),
                in_study_period=bool(f),
            )
            for d, y, f in zip(
                rf["auction_date"], rf["implicit_yield_pct"], rf["in_study_period"], strict=True
            )
        ],
    )
