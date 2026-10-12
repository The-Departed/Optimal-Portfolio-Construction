"""CAPM orchestration (Phase 4)."""

from app.core.errors import AnalysisNotImplementedError
from app.schemas.capm import CapmSummaryResponse
from app.services.data_status_service import DataStatusService


class CapmService:
    def __init__(self, data_status: DataStatusService) -> None:
        self._data_status = data_status

    def summary(self) -> CapmSummaryResponse:
        self._data_status.require_ready()
        raise AnalysisNotImplementedError("CAPM analysis is scheduled for Phase 4.")
