from fastapi import APIRouter

from app.api.dependencies import DataStatusServiceDep
from app.schemas.data_status import DataStatusResponse

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/status", response_model=DataStatusResponse)
def data_status(service: DataStatusServiceDep) -> DataStatusResponse:
    return service.get_status()
