"""FastAPI dependency providers wiring settings into services."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.analytics_service import AnalyticsService
from app.services.capm_service import CapmService
from app.services.data_status_service import DataStatusService
from app.services.portfolio_service import PortfolioService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_data_status_service(settings: SettingsDep) -> DataStatusService:
    return DataStatusService(settings)


DataStatusServiceDep = Annotated[DataStatusService, Depends(get_data_status_service)]


def get_capm_service(data_status: DataStatusServiceDep) -> CapmService:
    return CapmService(data_status)


def get_portfolio_service(data_status: DataStatusServiceDep) -> PortfolioService:
    return PortfolioService(data_status)


CapmServiceDep = Annotated[CapmService, Depends(get_capm_service)]
PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]


def get_analytics_service(settings: SettingsDep) -> AnalyticsService:
    return AnalyticsService(settings)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
