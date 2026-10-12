from fastapi import APIRouter

from app import __version__
from app.api.dependencies import SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        service=settings.app_name, version=__version__, environment=settings.environment
    )
