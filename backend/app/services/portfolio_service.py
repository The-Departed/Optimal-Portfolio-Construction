"""Portfolio simulation and optimization orchestration (Phases 5-6)."""

from app.core.errors import AnalysisNotImplementedError
from app.schemas.portfolio import (
    OptimizationRequest,
    OptimizationResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.services.data_status_service import DataStatusService


class PortfolioService:
    def __init__(self, data_status: DataStatusService) -> None:
        self._data_status = data_status

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        self._data_status.require_ready()
        raise AnalysisNotImplementedError("Monte Carlo simulation is scheduled for Phase 5.")

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        self._data_status.require_ready()
        raise AnalysisNotImplementedError("Constrained optimization is scheduled for Phase 6.")
