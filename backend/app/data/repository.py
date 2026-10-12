"""Read-only access to processed data.

The Phase 2 pipeline writes ``data/processed/manifest.json`` last, after every
validation check has run, and ``data/reports/validation_summary.json`` with the
per-dataset results. The manifest is the single source of truth for whether
analyses may use the processed dataset.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = "manifest.json"
VALIDATION_SUMMARY_FILENAME = "validation_summary.json"


class ManifestError(ValueError):
    """A dataset artifact exists but cannot be parsed or lacks required fields."""


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    generated_at: datetime
    validation_passed: bool
    files: dict[str, str]
    overall_status: str | None = None
    pipeline_version: str | None = None
    reports: dict[str, str] = field(default_factory=dict)


class DataRepository:
    def __init__(self, processed_dir: Path, reports_dir: Path | None = None) -> None:
        self._processed_dir = processed_dir
        self._reports_dir = reports_dir or processed_dir.parent / "reports"

    @property
    def manifest_path(self) -> Path:
        return self._processed_dir / MANIFEST_FILENAME

    @property
    def validation_summary_path(self) -> Path:
        return self._reports_dir / VALIDATION_SUMMARY_FILENAME

    def load_manifest(self) -> DatasetManifest | None:
        """Return the manifest, ``None`` if absent, or raise ``ManifestError``."""
        raw = self._read_json(self.manifest_path)
        if raw is None:
            return None
        try:
            return DatasetManifest(
                generated_at=datetime.fromisoformat(raw["generated_at"]),
                validation_passed=bool(raw["validation_passed"]),
                files=dict(raw.get("files", {})),
                overall_status=raw.get("overall_status"),
                pipeline_version=raw.get("pipeline_version"),
                reports=dict(raw.get("reports", {})),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError(f"Invalid dataset manifest at {self.manifest_path}: {exc}") from exc

    def load_validation_summary(self) -> dict[str, Any] | None:
        """Return the validation summary, ``None`` if absent, or raise ``ManifestError``."""
        raw = self._read_json(self.validation_summary_path)
        if raw is not None and not isinstance(raw.get("datasets"), dict):
            raise ManifestError(
                f"Validation summary at {self.validation_summary_path} has no datasets"
            )
        return raw

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"Unreadable JSON at {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ManifestError(f"Unexpected JSON structure at {path}")
        return raw
