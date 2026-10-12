from fastapi import APIRouter

from app.api.dependencies import CapmServiceDep
from app.schemas.capm import CapmSummaryResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/capm", tags=["capm"])

_ERRORS = {501: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/summary", response_model=CapmSummaryResponse, responses=_ERRORS)
def capm_summary(service: CapmServiceDep) -> CapmSummaryResponse:
    return service.summary()
