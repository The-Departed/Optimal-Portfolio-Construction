"""Analytics API against a SYNTHETIC validated dataset produced by the Phase 2 pipeline.

Expected values are recomputed independently from the processed CSVs with plain
pandas/numpy, not with the analytics module under test.
"""

import json
import math
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.assets import ASSET_IDS
from app.main import create_app
from app.services.analytics_service import AnalyticsService, clear_cache, persist


@pytest.fixture
def api(analytics_settings: Settings) -> TestClient:
    clear_cache()
    return TestClient(create_app(analytics_settings))


@pytest.fixture
def prices(analytics_settings: Settings) -> pd.DataFrame:
    path = analytics_settings.processed_dir / "prices" / "portfolio_prices_aligned.csv"
    return pd.read_csv(path, index_col="date", parse_dates=["date"])


def test_summary(api: TestClient, prices: pd.DataFrame) -> None:
    body = api.get("/api/v1/analytics/summary").json()
    assert body["status"] in ("PASS", "PASS_WITH_WARNINGS")
    assert body["assets"] == list(ASSET_IDS) and body["benchmark"] == "NIFTY50"
    assert body["sample"]["observations"] == len(prices) - 1
    assert body["sample"]["price_start"] == prices.index[0].date().isoformat()
    checks = {c["name"]: c["status"] for c in body["checks"]}
    assert checks["returns_reproduce_phase2"] == "pass"
    assert checks["covariance_matrix"] == "pass"
    assert checks["risk_free_conversion"] == "warn"
    assert body["conventions"]["periods_per_year"] == 252
    assert body["risk_free"]["frequency"] == "weekly"


def test_statistics_match_independent_calculation(api: TestClient, prices: pd.DataFrame) -> None:
    body = api.get("/api/v1/analytics/statistics", params={"series": "TCS"}).json()
    (row,) = body["series"]
    p = prices["TCS"]
    r = (p / p.shift(1) - 1).iloc[1:]
    assert row["observations"] == len(r)
    assert row["mean_daily"] == pytest.approx(r.mean())
    assert row["median_daily"] == pytest.approx(r.median())
    assert row["std_daily"] == pytest.approx(r.std(ddof=1))
    assert row["annualized_volatility"] == pytest.approx(r.std(ddof=1) * math.sqrt(252))
    days = (p.index[-1] - p.index[0]).days
    assert row["annualized_return"] == pytest.approx(
        (p.iloc[-1] / p.iloc[0]) ** (365.25 / days) - 1
    )
    assert row["cumulative_return"] == pytest.approx(p.iloc[-1] / p.iloc[0] - 1)


def test_statistics_default_order_and_individual_sample(api: TestClient) -> None:
    common = api.get("/api/v1/analytics/statistics").json()
    assert [s["series_id"] for s in common["series"]] == [*ASSET_IDS, "NIFTY50"]
    indiv = api.get(
        "/api/v1/analytics/statistics", params={"sample": "individual", "series": "GSEC"}
    ).json()
    gsec_common = next(s for s in common["series"] if s["series_id"] == "GSEC")
    # The NAV series has its own (different) sample: the bank-holiday NAV gap is absent
    # from its own history but the common sample also loses other series' gaps.
    assert indiv["series"][0]["observations"] >= gsec_common["observations"]


def test_correlation_and_covariance(api: TestClient, prices: pd.DataFrame) -> None:
    r = (prices / prices.shift(1) - 1).iloc[1:]
    corr = api.get("/api/v1/analytics/correlation").json()
    assert corr["labels"] == list(ASSET_IDS)
    np.testing.assert_allclose(np.array(corr["values"]), r.corr().to_numpy(), atol=1e-12)
    assert corr["diagnostics"]["valid"] and corr["observations"] == len(r)
    assert np.all(np.array(corr["pairwise_observations"]) == len(r))
    daily = api.get("/api/v1/analytics/covariance", params={"frequency": "daily"}).json()
    annual = api.get("/api/v1/analytics/covariance").json()
    np.testing.assert_allclose(np.array(daily["values"]), r.cov(ddof=1).to_numpy(), rtol=1e-10)
    np.testing.assert_allclose(
        np.array(annual["values"]), np.array(daily["values"]) * 252, rtol=1e-12
    )
    assert annual["frequency"] == "annualized" and annual["diagnostics"]["positive_semidefinite"]


def test_returns_window_and_validation(api: TestClient, prices: pd.DataFrame) -> None:
    body = api.get(
        "/api/v1/analytics/returns",
        params={"series": "GOLD,NIFTY50", "start": "2024-02-01", "end": "2024-02-29"},
    ).json()
    assert body["series_ids"] == ["GOLD", "NIFTY50"]
    assert body["start"] >= "2024-02-01" and body["end"] <= "2024-02-29"
    assert (
        len(body["dates"])
        == len(body["returns"]["GOLD"])
        == len(body["sessions_spanned"])
        == body["observations"]
    )
    assert (
        api.get("/api/v1/analytics/returns", params={"series": "RF_TBILL_91D"}).status_code == 422
    )
    assert (
        api.get(
            "/api/v1/analytics/returns", params={"start": "2030-01-01", "end": "2030-02-01"}
        ).status_code
        == 422
    )
    assert api.get("/api/v1/analytics/returns", params={"start": "01-02-2024"}).status_code == 422


def test_distribution_and_risk_free(api: TestClient) -> None:
    dist = api.get("/api/v1/analytics/distribution", params={"series": "MM", "bins": 12}).json()
    assert sum(dist["counts"]) == dist["observations"] and len(dist["bin_edges"]) == 13
    assert (
        api.get("/api/v1/analytics/distribution", params={"series": "MM", "bins": 1}).status_code
        == 422
    )
    rf = api.get("/api/v1/analytics/risk-free").json()
    assert rf["profile"]["units"] == "percent per annum"
    assert rf["profile"]["conversion_status"] == "pending_approval"
    assert all(5 < o["implicit_yield_pct"] < 8 for o in rf["observations"])


def test_unavailable_when_data_missing(settings: Settings) -> None:
    clear_cache()
    body = TestClient(create_app(settings)).get("/api/v1/analytics/summary")
    assert body.status_code == 503 and body.json()["code"] == "DATA_NOT_READY"


def test_unavailable_when_processed_file_missing(analytics_settings: Settings) -> None:
    clear_cache()
    (analytics_settings.processed_dir / "returns" / "portfolio_returns_aligned.csv").unlink()
    res = TestClient(create_app(analytics_settings)).get("/api/v1/analytics/statistics")
    assert res.status_code == 503 and "portfolio_returns_aligned.csv" in res.json()["message"]


def test_persisted_outputs(analytics_settings: Settings) -> None:
    clear_cache()
    files = persist(AnalyticsService(analytics_settings).result(), analytics_settings.data_dir)
    root = analytics_settings.data_dir.parent
    for rel in files.values():
        assert (root / rel).is_file()
    corr = pd.read_csv(root / files["correlation_matrix"], index_col="asset_id")
    assert list(corr.index) == list(corr.columns) == list(ASSET_IDS)
    stats = pd.read_csv(root / files["descriptive_statistics"])
    assert set(stats["sample"]) == {"common", "individual"}
    summary = json.loads((root / files["analytics_summary"]).read_text())
    for key in (
        "source_dataset",
        "computed_at",
        "analytics_version",
        "conventions",
        "sample",
        "status",
        "missing_data_policy",
    ):
        assert key in summary
    assert summary["conventions"]["periods_per_year"] == 252
    # Phase 2 artifacts are untouched.
    manifest = json.loads((analytics_settings.processed_dir / "manifest.json").read_text())
    assert "asset_daily_returns" not in json.dumps(manifest)


def test_run_analytics_cli(analytics_settings: Settings) -> None:
    env = {
        "APP_DATA_DIR": str(analytics_settings.data_dir),
        "APP_STUDY_START": "2024-01-01",
        "APP_STUDY_END": "2024-03-29",
        "APP_ANALYTICS_MIN_ANNUALIZATION_DAYS": "30",
        "PATH": "",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.run_analytics"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ANALYTICS STATUS" in proc.stdout
