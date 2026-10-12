"""Portfolio simulation (Phase 5), optimization and frontier (Phase 6) orchestration."""

from app.core.config import Settings
from app.schemas.portfolio import (
    FrontierResponse,
    OptimizationRequest,
    OptimizationResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.services import optimization_service, simulation_service
from app.services.data_status_service import DataStatusService


class PortfolioService:
    def __init__(self, settings: Settings, data_status: DataStatusService) -> None:
        self._settings = settings
        self._data_status = data_status

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        self._data_status.require_ready()
        run = simulation_service.run(self._settings, request)
        return simulation_service.to_response(run, request.scatter_points)

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        self._data_status.require_ready()
        return optimization_service.optimize(self._settings, request)

    def frontier(self, points: int) -> FrontierResponse:
        self._data_status.require_ready()
        return optimization_service.frontier(self._settings, points)
