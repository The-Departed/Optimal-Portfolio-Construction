"""Determines whether a validated dataset is available for analysis.

Readiness comes only from pipeline artifacts: the manifest's ``validation_passed``
flag, cross-checked against ``validation_summary.json``. Nothing is hardcoded.
"""

from typing import Any

from app.core.config import Settings
from app.core.errors import DataNotReadyError
from app.data.repository import DataRepository, ManifestError
from app.schemas.data_status import (
    CommonPeriod,
    DatasetState,
    DatasetStatusOut,
    DataStatusResponse,
)


class DataStatusService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = DataRepository(settings.processed_dir, settings.reports_dir)

    def get_status(self) -> DataStatusResponse:
        common = {
            "manifest_path": self._display_path(),
            "study_start": self._settings.study_start.isoformat(),
            "study_end": self._settings.study_end.isoformat(),
        }
        try:
            manifest = self._repository.load_manifest()
            summary = self._repository.load_validation_summary() if manifest else None
        except ManifestError as exc:
            return DataStatusResponse(
                ready=False, state=DatasetState.INVALID, message=str(exc), **common
            )
        if manifest is None:
            return DataStatusResponse(
                ready=False,
                state=DatasetState.MISSING,
                message="No processed dataset found. Data acquisition has not been run yet.",
                **common,
            )
        if summary is None or summary.get("overall_status") != manifest.overall_status:
            return DataStatusResponse(
                ready=False,
                state=DatasetState.INVALID,
                message="The validation summary is missing or inconsistent with the manifest. "
                "Re-run the data pipeline.",
                generated_at=manifest.generated_at,
                **common,
            )

        details = self._details(summary)
        details["overall_status"] = manifest.overall_status
        details["pipeline_version"] = manifest.pipeline_version
        if not manifest.validation_passed:
            return DataStatusResponse(
                ready=False,
                state=DatasetState.VALIDATION_FAILED,
                message="The dataset is BLOCKED by failed validation checks. "
                "See data/reports/data_quality_report.md.",
                generated_at=manifest.generated_at,
                **common,
                **details,
            )
        with_warnings = manifest.overall_status == "PASS_WITH_WARNINGS"
        return DataStatusResponse(
            ready=True,
            state=DatasetState.READY,
            message="Validated dataset available"
            + (" with documented warnings and limitations." if with_warnings else "."),
            generated_at=manifest.generated_at,
            **common,
            **details,
        )

    @staticmethod
    def _details(summary: dict[str, Any]) -> dict[str, Any]:
        datasets = []
        for ds_id, d in summary["datasets"].items():
            checks = d.get("checks", [])
            datasets.append(
                DatasetStatusOut(
                    dataset_id=ds_id,
                    name=d["name"],
                    role=d["role"],
                    critical=bool(d.get("critical")),
                    status=d["status"],
                    source=d.get("source", ""),
                    identifier=str(d.get("identifier", "")),
                    frequency=d.get("frequency", ""),
                    first_date=d.get("first_date"),
                    last_date=d.get("last_date"),
                    observations=d.get("observations"),
                    session_coverage=d.get("session_coverage"),
                    failures=[
                        f"{c['name']}: {c['detail']}" for c in checks if c["status"] == "fail"
                    ],
                    warnings=[
                        f"{c['name']}: {c['detail']}" for c in checks if c["status"] == "warn"
                    ],
                    known_limitations=list(d.get("known_limitations", [])),
                )
            )
        period = summary.get("common_period")
        return {
            "common_period": CommonPeriod(**period) if period else None,
            "datasets": datasets,
            "critical_failures": list(summary.get("critical_failures", [])),
            "warnings": list(summary.get("warnings", [])),
            "known_limitations": list(summary.get("known_limitations", [])),
        }

    def _display_path(self) -> str:
        # Report a path relative to the project so local directories are not exposed.
        path = self._repository.manifest_path
        return path.relative_to(self._settings.data_dir.parent).as_posix()

    def require_ready(self) -> None:
        status = self.get_status()
        if not status.ready:
            raise DataNotReadyError(status.message, details={"state": status.state.value})
