import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fixtures.synthetic import STUDY_END, STUDY_START


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-online", action="store_true", help="run tests that contact live data sources"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-online"):
        return
    skip = pytest.mark.skip(reason="online test: pass --run-online to enable")
    for item in items:
        if "online" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    for sub in ("raw", "interim", "processed", "reports"):
        (tmp_path / "data" / sub).mkdir(parents=True)
    return tmp_path / "data"


@pytest.fixture
def settings(data_dir: Path) -> Settings:
    return Settings(environment="test", data_dir=data_dir)


@pytest.fixture
def pipeline_settings(data_dir: Path) -> Settings:
    """Settings for synthetic pipeline runs (short study period, no HTTP pauses)."""
    return Settings(
        environment="test",
        data_dir=data_dir,
        study_start=STUDY_START,
        study_end=STUDY_END,
        http_pause_seconds=0,
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def write_manifest(data_dir: Path) -> Callable[[object], Path]:
    def _write(content: object) -> Path:
        path = data_dir / "processed" / "manifest.json"
        text = content if isinstance(content, str) else json.dumps(content)
        path.write_text(text, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def write_artifacts(data_dir: Path) -> Callable[..., None]:
    """Write a minimal, mutually consistent manifest + validation summary."""

    def _write(overall: str = "PASS_WITH_WARNINGS", **summary_extra: Any) -> None:
        passed = overall != "BLOCKED"
        (data_dir / "processed" / "manifest.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "validation_passed": passed,
                    "overall_status": overall,
                    "pipeline_version": "test",
                    "files": {},
                }
            ),
            encoding="utf-8",
        )
        summary = {
            "overall_status": overall,
            "common_period": {
                "first": "2019-01-02",
                "last": "2025-12-31",
                "price_dates": 10,
                "return_observations": 9,
                "session_coverage": 0.99,
            },
            "critical_failures": [] if passed else ["GSEC: coverage: synthetic failure"],
            "warnings": [],
            "known_limitations": [],
            "datasets": {
                "GSEC": {
                    "name": "Synthetic bond",
                    "role": "portfolio_asset",
                    "critical": True,
                    "status": "PASS" if passed else "FAIL",
                    "source": "test",
                    "identifier": "X",
                    "frequency": "daily",
                    "checks": []
                    if passed
                    else [{"name": "coverage", "status": "fail", "detail": "x"}],
                }
            },
            **summary_extra,
        }
        (data_dir / "reports" / "validation_summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )

    return _write


@pytest.fixture
def analytics_settings(pipeline_settings: Settings) -> Settings:
    """A validated SYNTHETIC Phase 2 dataset on disk, ready for Phase 3 analytics.

    The synthetic sample spans about three months, so the CAGR minimum interval is
    lowered for tests; production keeps 365 days.
    """
    from app.data_pipeline.pipeline import DataPipeline
    from tests.fixtures.synthetic import fake_downloaders

    DataPipeline(pipeline_settings, downloaders=fake_downloaders()).run()
    return pipeline_settings.model_copy(update={"analytics_min_annualization_days": 30})
