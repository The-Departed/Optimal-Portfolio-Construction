"""Dataset readiness schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.common import ApiModel


class DatasetState(StrEnum):
    MISSING = "missing"
    INVALID = "invalid"
    VALIDATION_FAILED = "validation_failed"
    READY = "ready"


class CommonPeriod(ApiModel):
    first: str
    last: str
    price_dates: int
    return_observations: int
    session_coverage: float | None = None


class DatasetStatusOut(ApiModel):
    dataset_id: str
    name: str
    role: str
    critical: bool
    status: str = Field(description="PASS, PASS_WITH_WARNINGS, FAIL or NOT_RETRIEVED")
    source: str
    identifier: str
    frequency: str
    first_date: str | None = None
    last_date: str | None = None
    observations: int | None = None
    session_coverage: float | None = None
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)


class DataStatusResponse(ApiModel):
    ready: bool = Field(description="True only when a validated dataset is available.")
    state: DatasetState
    message: str
    manifest_path: str
    generated_at: datetime | None = None
    study_start: str
    study_end: str
    overall_status: str | None = Field(
        default=None, description="PASS, PASS_WITH_WARNINGS or BLOCKED from the pipeline."
    )
    pipeline_version: str | None = None
    common_period: CommonPeriod | None = None
    datasets: list[DatasetStatusOut] = Field(default_factory=list)
    critical_failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
