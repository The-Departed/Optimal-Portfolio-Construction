from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import AnalyticsServiceDep
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    CovarianceFrequency,
    DistributionResponse,
    MatrixResponse,
    ReturnsResponse,
    RiskFreeResponse,
    Sample,
    StatisticsResponse,
)
from app.schemas.common import ErrorResponse
from app.services import analytics_queries as q

router = APIRouter(prefix="/analytics", tags=["analytics"])

_ERRORS = {422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}
SeriesParam = Annotated[
    list[str] | None,
    Query(description="Series identifiers (repeat or comma-separate); default: all"),
]


@router.get("/summary", response_model=AnalyticsSummaryResponse, responses=_ERRORS)
def analytics_summary(service: AnalyticsServiceDep) -> AnalyticsSummaryResponse:
    return q.summary(service.result())


@router.get("/statistics", response_model=StatisticsResponse, responses=_ERRORS)
def analytics_statistics(
    service: AnalyticsServiceDep,
    sample: Sample = Sample.COMMON,
    series: SeriesParam = None,
) -> StatisticsResponse:
    ids = q.resolve_series(series)
    return q.statistics(service.result(), sample, ids)


@router.get("/correlation", response_model=MatrixResponse, responses=_ERRORS)
def analytics_correlation(service: AnalyticsServiceDep) -> MatrixResponse:
    return q.correlation(service.result())


@router.get("/covariance", response_model=MatrixResponse, responses=_ERRORS)
def analytics_covariance(
    service: AnalyticsServiceDep,
    frequency: CovarianceFrequency = CovarianceFrequency.ANNUALIZED,
) -> MatrixResponse:
    return q.covariance(service.result(), frequency)


@router.get("/returns", response_model=ReturnsResponse, responses=_ERRORS)
def analytics_returns(
    service: AnalyticsServiceDep,
    series: SeriesParam = None,
    start: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    end: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
) -> ReturnsResponse:
    ids = q.resolve_series(series)
    return q.returns(service.result(), ids, start, end)


@router.get("/distribution", response_model=DistributionResponse, responses=_ERRORS)
def analytics_distribution(
    service: AnalyticsServiceDep,
    series: Annotated[str, Query(description="One series identifier")],
    sample: Sample = Sample.COMMON,
    bins: Annotated[int, Query(ge=5, le=200)] = 50,
) -> DistributionResponse:
    return q.distribution(service.result(), q.single_series(series), sample, bins)


@router.get("/risk-free", response_model=RiskFreeResponse, responses=_ERRORS)
def analytics_risk_free(service: AnalyticsServiceDep) -> RiskFreeResponse:
    return q.risk_free(service.result())
