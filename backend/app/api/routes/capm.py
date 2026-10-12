from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import CapmServiceDep
from app.schemas.capm import CapmSummaryResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/capm", tags=["capm"])

_ERRORS = {422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/summary", response_model=CapmSummaryResponse, responses=_ERRORS)
def capm_summary(
    service: CapmServiceDep,
    equities: Annotated[
        list[str] | None,
        Query(description="Equity identifiers (repeat or comma-separate); default: all six"),
    ] = None,
) -> CapmSummaryResponse:
    return service.summary(equities)
