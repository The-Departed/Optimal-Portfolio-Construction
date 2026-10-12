"""Descriptive analytics contracts (Phase 3).

All returns and volatilities are decimals (0.12 == 12%). Daily and annualized
quantities are distinguished by field name.
"""

from enum import StrEnum

from pydantic import Field

from app.schemas.common import ApiModel


class Sample(StrEnum):
    COMMON = "common"
    INDIVIDUAL = "individual"


class CovarianceFrequency(StrEnum):
    DAILY = "daily"
    ANNUALIZED = "annualized"


class AnalyticsCheck(ApiModel):
    name: str
    status: str = Field(description="pass, warn or fail")
    detail: str


class SampleInfo(ApiModel):
    start: str = Field(description="First return date (the first price date has no return)")
    end: str
    price_start: str
    observations: int
    multi_session_returns: int


class RiskFreeProfileOut(ApiModel):
    series_id: str
    measure: str
    units: str
    day_count: str
    frequency: str
    observations: int
    first_date: str
    last_date: str
    lookback_observations: int
    median_gap_days: float
    max_gap_days: int
    min_yield_pct: float
    max_yield_pct: float
    mean_yield_pct: float
    conversion_status: str
    proposed_conversion: str
    limitations: list[str]


class AnalyticsSummaryResponse(ApiModel):
    status: str = Field(description="PASS, PASS_WITH_WARNINGS or FAILED")
    analytics_version: str
    computed_at: str
    dataset_generated_at: str
    dataset_status: str
    sample: SampleInfo
    assets: list[str]
    benchmark: str
    checks: list[AnalyticsCheck]
    conventions: dict[str, object]
    risk_free: RiskFreeProfileOut | None
    upstream_warnings: list[str]
    disclaimer: str


class SeriesStatistics(ApiModel):
    series_id: str
    name: str
    role: str = Field(description="portfolio_asset or benchmark")
    observations: int
    start: str
    end: str
    mean_daily: float | None
    median_daily: float | None
    std_daily: float | None
    min_daily: float | None
    max_daily: float | None
    skewness: float | None
    excess_kurtosis: float | None
    cumulative_return: float | None
    annualized_return: float | None = Field(description="CAGR over elapsed calendar time")
    annualized_mean_return: float | None = Field(description="Arithmetic mean daily x 252")
    annualized_volatility: float | None
    elapsed_calendar_days: int | None
    notes: list[str]


class StatisticsResponse(ApiModel):
    sample: Sample
    periods_per_year: int
    calendar_days_per_year: float
    series: list[SeriesStatistics]


class MatrixDiagnosticsOut(ApiModel):
    symmetric: bool
    max_asymmetry: float
    finite: bool
    positive_semidefinite: bool
    min_eigenvalue: float
    max_eigenvalue: float
    condition_number: float | None
    valid: bool
    problems: list[str]


class MatrixResponse(ApiModel):
    kind: str = Field(description="correlation or covariance")
    frequency: CovarianceFrequency | None = None
    labels: list[str]
    values: list[list[float]]
    observations: int
    pairwise_observations: list[list[int]]
    start: str
    end: str
    diagnostics: MatrixDiagnosticsOut


class ReturnsResponse(ApiModel):
    start: str
    end: str
    observations: int
    series_ids: list[str]
    dates: list[str]
    returns: dict[str, list[float]] = Field(description="Daily simple returns per series")
    sessions_spanned: list[int]


class DistributionResponse(ApiModel):
    series_id: str
    sample: Sample
    observations: int
    bin_edges: list[float]
    counts: list[int]
    mean_daily: float | None
    std_daily: float | None


class RiskFreeObservation(ApiModel):
    auction_date: str
    implicit_yield_pct: float
    in_study_period: bool


class RiskFreeResponse(ApiModel):
    profile: RiskFreeProfileOut | None
    error: str | None
    observations: list[RiskFreeObservation]
