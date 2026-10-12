"""Schemas shared across API modules."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DATA_NOT_READY = "DATA_NOT_READY"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"
    INFEASIBLE_CONSTRAINT = "INFEASIBLE_CONSTRAINT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(ApiModel):
    code: ErrorCode
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class HealthResponse(ApiModel):
    status: str = "ok"
    service: str
    version: str
    environment: str


class AssetOut(ApiModel):
    id: str
    name: str
    asset_class: str
    sector: str
    instrument: str
    symbol: str | None
    source: str
    verified: bool
    notes: str


class ReferenceSeriesOut(ApiModel):
    id: str
    name: str
    role: str
    symbol: str | None
    source: str
    verified: bool
    notes: str


class AssetUniverseResponse(ApiModel):
    assets: list[AssetOut] = Field(description="Portfolio assets in canonical order.")
    benchmark: ReferenceSeriesOut
    risk_free: ReferenceSeriesOut


class PortfolioMetrics(ApiModel):
    """Annualized portfolio statistics; all values are decimals (0.12 == 12%)."""

    expected_return: float
    volatility: float = Field(ge=0)
    sharpe_ratio: float
