"""End-to-end pipeline runs against SYNTHETIC sources (see tests/fixtures/synthetic.py)."""

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.data_pipeline.cli import main as cli_main
from app.data_pipeline.pipeline import DataPipeline, PipelineOptions
from app.data_pipeline.quality_checks import DatasetStatus, OverallStatus
from app.domain.assets import ASSET_IDS
from app.main import create_app
from tests.fixtures.synthetic import Scenario, fake_downloaders


def _run(settings: Settings, scenario: Scenario | None = None, **opts):
    pipeline = DataPipeline(settings, downloaders=fake_downloaders(scenario))
    return pipeline.run(PipelineOptions(**opts))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_fixture_produces_ready_dataset(pipeline_settings: Settings) -> None:
    result = _run(pipeline_settings)
    s = pipeline_settings
    assert result.overall is OverallStatus.PASS_WITH_WARNINGS  # documented limitations remain
    assert result.ready and not result.critical_failures
    assert all(
        result.datasets[i].status in (DatasetStatus.PASS, DatasetStatus.PASS_WITH_WARNINGS)
        for i in [*ASSET_IDS, "NIFTY50", "RF_TBILL_91D"]
    )
    prices = pd.read_csv(
        s.processed_dir / "prices" / "portfolio_prices_aligned.csv", index_col="date"
    )
    returns = pd.read_csv(
        s.processed_dir / "returns" / "portfolio_returns_aligned.csv", index_col="date"
    )
    assert list(prices.columns) == list(ASSET_IDS)
    assert len(returns) == len(prices) - 1
    assert not prices.isna().any().any() and not returns.isna().any().any()
    bench = pd.read_csv(
        s.processed_dir / "returns" / "benchmark_returns_aligned.csv", index_col="date"
    )
    assert list(bench.columns) == ["NIFTY50"] and bench.index.equals(returns.index)
    # The bank-only holiday has no NAV: it is explained, dropped, and never filled.
    assert "2024-02-19" not in prices.index
    assert result.datasets["GSEC"].quality.coverage["sessions_not_expected"] == 1

    manifest = _read(s.processed_dir / "manifest.json")
    summary = _read(s.reports_dir / "validation_summary.json")
    assert manifest["validation_passed"] is True
    assert manifest["overall_status"] == summary["overall_status"] == "PASS_WITH_WARNINGS"
    for name in (
        "data_quality_report.md",
        "coverage_report.csv",
        "missing_values_report.csv",
        "source_manifest.json",
    ):
        assert (s.reports_dir / name).is_file()
    rf = pd.read_csv(s.processed_dir / "risk_free" / "RF_TBILL_91D.csv")
    assert {"auction_date", "implicit_yield_pct", "in_study_period"} <= set(rf.columns)
    assert not rf["in_study_period"].iloc[0]  # lookback auction retained for as-of use


def test_source_manifest_serialization(pipeline_settings: Settings) -> None:
    _run(pipeline_settings)
    manifest = _read(pipeline_settings.reports_dir / "source_manifest.json")
    entry = next(d for d in manifest["datasets"] if d["dataset_id"] == "GSEC")
    for key in (
        "identifier",
        "source_url",
        "retrieved_at",
        "requested_range",
        "actual_range",
        "frequency",
        "selected_field",
        "currency",
        "units",
        "files",
        "validation_status",
        "known_limitations",
        "retrieval_status",
    ):
        assert key in entry
    assert entry["selected_field"] == "Net Asset Value"
    assert "secret" not in json.dumps(manifest).lower()


def test_missing_and_duplicate_observations_are_detected(pipeline_settings: Settings) -> None:
    scenario = Scenario(
        drop_dates={"TCS": ["2024-02-07"]},
        duplicate_dates={"HDFCBANK": ["2024-01-10"]},
        bad_values={"MM": {"2024-01-15": "abc"}},
    )
    result = _run(pipeline_settings, scenario)
    assert result.datasets["HDFCBANK"].quality.missing["duplicate_dates"] == 1
    mm = result.datasets["MM"].quality.missing
    assert mm["non_numeric"] == 1 and mm["excluded_by_reason"] == {"non_numeric": 1}
    excluded = pd.read_csv(pipeline_settings.reports_dir / "excluded_records.csv")
    assert {"MM", "HDFCBANK"} <= set(excluded["dataset_id"])
    # A date missing in one series is removed from the common sample, not filled.
    prices = pd.read_csv(
        pipeline_settings.processed_dir / "prices" / "portfolio_prices_aligned.csv",
        index_col="date",
    )
    assert "2024-01-15" not in prices.index


def test_source_error_detected_against_reference(pipeline_settings: Settings) -> None:
    result = _run(pipeline_settings, Scenario(scale_dates={"GOLD": {"2024-02-01": 0.01}}))
    gold = result.datasets["GOLD"]
    assert gold.quality.missing["excluded_by_reason"] == {"source_error": 1}
    assert gold.status is DatasetStatus.PASS_WITH_WARNINGS


def test_failed_critical_download_blocks(pipeline_settings: Settings) -> None:
    result = _run(pipeline_settings, Scenario(fail={"GSEC"}))
    assert result.overall is OverallStatus.BLOCKED
    gsec = result.datasets["GSEC"]
    assert gsec.status is DatasetStatus.NOT_RETRIEVED and gsec.retrieval_status == "failed"
    assert not (pipeline_settings.raw_dir / "bonds" / "GSEC").exists()  # no placeholder raw data
    assert not (
        pipeline_settings.processed_dir / "prices" / "portfolio_prices_aligned.csv"
    ).exists()
    manifest = _read(pipeline_settings.processed_dir / "manifest.json")
    assert manifest["validation_passed"] is False
    entry = next(
        d
        for d in _read(pipeline_settings.reports_dir / "source_manifest.json")["datasets"]
        if d["dataset_id"] == "GSEC"
    )
    assert (
        entry["retrieval_status"] == "failed"
        and "synthetic network failure" in entry["retrieval_error"]
    )


def test_failed_cross_check_download_does_not_block(pipeline_settings: Settings) -> None:
    result = _run(pipeline_settings, Scenario(fail={"GSEC_EXCHANGE"}))
    assert result.overall is OverallStatus.PASS_WITH_WARNINGS
    assert any("GSEC_EXCHANGE" in w for w in result.warnings)


def test_insufficient_history_blocks(pipeline_settings: Settings) -> None:
    result = _run(pipeline_settings, Scenario(late_start={"GOLD": "2024-03-01"}))
    assert result.datasets["GOLD"].status is DatasetStatus.FAIL
    assert result.overall is OverallStatus.BLOCKED
    assert any(m.startswith("GOLD: period_boundaries") for m in result.critical_failures)


def test_cached_raw_data_is_reused_and_outputs_are_repeatable(pipeline_settings: Settings) -> None:
    scenario = Scenario()
    _run(pipeline_settings, scenario)
    first = {
        p.name: p.read_bytes() for p in (pipeline_settings.processed_dir / "returns").glob("*.csv")
    }
    calls = len(scenario.calls)
    result = _run(pipeline_settings, scenario, offline=True)
    assert len(scenario.calls) == calls  # no new downloads
    assert all(r.retrieval_status == "cached" for r in result.datasets.values())
    second = {
        p.name: p.read_bytes() for p in (pipeline_settings.processed_dir / "returns").glob("*.csv")
    }
    assert first == second


def test_offline_without_cache_reports_not_retrieved(pipeline_settings: Settings) -> None:
    result = _run(pipeline_settings, offline=True)
    assert result.overall is OverallStatus.BLOCKED
    assert all(r.status is DatasetStatus.NOT_RETRIEVED for r in result.datasets.values())


def test_blocked_rerun_removes_stale_outputs(pipeline_settings: Settings) -> None:
    _run(pipeline_settings)
    aligned = pipeline_settings.processed_dir / "prices" / "portfolio_prices_aligned.csv"
    assert aligned.exists()
    _run(pipeline_settings, Scenario(fail={"TCS"}), refresh=True)
    assert not aligned.exists()


@pytest.mark.parametrize(("scenario", "code"), [(Scenario(), 0), (Scenario(fail={"NIFTY50"}), 1)])
def test_cli_exit_status(pipeline_settings: Settings, monkeypatch, scenario, code) -> None:
    monkeypatch.setattr("app.data_pipeline.cli.get_settings", lambda: pipeline_settings)
    factory = lambda s: DataPipeline(s, downloaders=fake_downloaders(scenario))  # noqa: E731
    assert cli_main([], pipeline_factory=factory) == code


def test_cli_strict_fails_on_warnings(pipeline_settings: Settings, monkeypatch) -> None:
    monkeypatch.setattr("app.data_pipeline.cli.get_settings", lambda: pipeline_settings)
    factory = lambda s: DataPipeline(s, downloaders=fake_downloaders())  # noqa: E731
    assert cli_main(["--strict"], pipeline_factory=factory) == 1


def test_data_status_api_reflects_pipeline(pipeline_settings: Settings) -> None:
    client = TestClient(create_app(pipeline_settings))
    _run(pipeline_settings)
    body = client.get("/api/v1/data/status").json()
    assert body["ready"] is True and body["overall_status"] == "PASS_WITH_WARNINGS"
    ids = {d["dataset_id"] for d in body["datasets"]}
    assert {*ASSET_IDS, "NIFTY50", "RF_TBILL_91D"} <= ids
    assert body["common_period"]["return_observations"] > 0

    _run(pipeline_settings, Scenario(fail={"RF_TBILL_91D"}), refresh=True)
    body = client.get("/api/v1/data/status").json()
    assert body["ready"] is False and body["state"] == "validation_failed"
    assert body["overall_status"] == "BLOCKED"
    assert any("RF_TBILL_91D" in m for m in body["critical_failures"])
