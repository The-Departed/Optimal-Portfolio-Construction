"""Portfolio simulation (Phase 5) and optimization (Phase 6) orchestration."""

from app.core.config import Settings
from app.core.errors import AnalysisNotImplementedError
from app.schemas.portfolio import (
    OptimizationRequest,
    OptimizationResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.services import simulation_service
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
        raise AnalysisNotImplementedError("Constrained optimization is scheduled for Phase 6.")
