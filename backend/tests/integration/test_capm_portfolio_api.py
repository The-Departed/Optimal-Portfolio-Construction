"""CAPM and Monte Carlo endpoints on a SYNTHETIC validated dataset (Phase 2 pipeline)."""

import gzip

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.assets import ASSET_IDS, EQUITY_IDS
from app.main import create_app
from app.services import analytics_service, simulation_service


@pytest.fixture
def api(analytics_settings: Settings) -> TestClient:
    analytics_service.clear_cache()
    simulation_service.clear_cache()
    return TestClient(create_app(analytics_settings))


def test_capm_summary(api: TestClient) -> None:
    body = api.get("/api/v1/capm/summary").json()
    assert [e["asset_id"] for e in body["equities"]] == list(EQUITY_IDS)
    assert body["market"]["series_id"] == "NIFTY50"
    assert 0 < body["risk_free"]["annualized_rate"] < 0.2
    for e in body["equities"]:
        assert e["status"] == "ok", e["error"]
        assert e["observations"] == body["observations"]
        assert e["jensens_alpha"] == pytest.approx(e["intercept_annualized"], abs=1e-10)
        assert e["jensens_alpha"] == pytest.approx(
            e["historical_mean_return"] - e["capm_expected_return"]
        )
        rf, rm = body["risk_free"]["annualized_rate"], body["market"]["mean_return"]
        assert e["capm_expected_return"] == pytest.approx(rf + e["beta"] * (rm - rf))
        assert 0 <= e["r_squared"] <= 1
    assert body["warnings"] and "intercept_daily" in body["definitions"]


def test_capm_filter_and_validation(api: TestClient) -> None:
    body = api.get("/api/v1/capm/summary", params={"equities": "TCS,MM"}).json()
    assert [e["asset_id"] for e in body["equities"]] == ["MM", "TCS"]
    res = api.get("/api/v1/capm/summary", params={"equities": "GSEC"})
    assert res.status_code == 422 and "six equities" in res.json()["message"]


def test_capm_failed_regression_is_not_reported_as_valid(api: TestClient, monkeypatch) -> None:
    from app.analytics.capm import CapmEstimationError

    def boom(*args, **kwargs):
        raise CapmEstimationError("synthetic failure")

    monkeypatch.setattr("app.services.capm_service.evaluate", boom)
    body = api.get("/api/v1/capm/summary").json()
    assert body["status"] == "FAILED"
    assert all(e["status"] == "failed" and e["beta"] is None for e in body["equities"])


def test_simulation(api: TestClient, analytics_settings: Settings) -> None:
    res = api.post(
        "/api/v1/portfolio/simulate", json={"n_portfolios": 2_000, "seed": 7, "scatter_points": 500}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["n_portfolios"] == 2_000 and body["seed"] == 7
    assert body["inputs"]["asset_order"] == list(ASSET_IDS)
    assert {c["status"] for c in body["checks"]} <= {"pass", "warn"}
    assert len(body["scatter"]["portfolio_ids"]) == 500
    labels = {c["label"]: c for c in body["candidates"]}
    assert set(labels) == {"min_volatility", "max_sharpe"}
    for c in body["candidates"]:
        w = [x["weight"] for x in c["weights"]]
        assert [x["asset_id"] for x in c["weights"]] == list(ASSET_IDS)
        assert min(w) >= 0 and sum(w) == pytest.approx(1.0)
    assert labels["min_volatility"]["volatility"] == pytest.approx(
        body["summary"]["volatility"]["min"]
    )
    assert labels["max_sharpe"]["sharpe_ratio"] == pytest.approx(
        body["summary"]["sharpe_ratio"]["max"]
    )
    assert "approximation" in body["frontier_label"]

    # Persisted file holds every portfolio and matches the response.
    path = analytics_settings.data_dir.parent / body["output_files"]["portfolios"]
    with gzip.open(path, "rt") as fh:
        df = pd.read_csv(fh)
    assert len(df) == 2_000
    weights = df[[f"w_{a}" for a in ASSET_IDS]].to_numpy()
    np.testing.assert_allclose(weights.sum(axis=1), 1.0, atol=1e-12)
    mu = np.array([body["inputs"]["expected_returns"][a] for a in ASSET_IDS])
    np.testing.assert_allclose(df["expected_return"], weights @ mu, rtol=1e-12)
    row = df.loc[labels["max_sharpe"]["portfolio_id"]]
    assert row["sharpe_ratio"] == pytest.approx(labels["max_sharpe"]["sharpe_ratio"])


def test_simulation_reproducible_by_seed(api: TestClient) -> None:
    def run(seed: int) -> dict:
        return api.post(
            "/api/v1/portfolio/simulate",
            json={"n_portfolios": 500, "seed": seed, "scatter_points": 100},
        ).json()

    a, b = run(3), run(3)
    simulation_service.clear_cache()
    c = run(3)
    d = run(4)
    assert a["scatter"] == b["scatter"] == c["scatter"]
    assert a["scatter"] != d["scatter"]


@pytest.mark.parametrize(
    "payload",
    [
        {"n_portfolios": 10},
        {"n_portfolios": 200_001},
        {"seed": -1},
        {"scatter_points": 50},
        {"n_portfolios": "x"},
    ],
)
def test_simulation_validation(api: TestClient, payload: dict) -> None:
    res = api.post("/api/v1/portfolio/simulate", json=payload)
    assert res.status_code == 422 and res.json()["code"] == "VALIDATION_ERROR"


def test_unavailable_without_data(settings: Settings) -> None:
    analytics_service.clear_cache()
    client = TestClient(create_app(settings))
    assert client.get("/api/v1/capm/summary").status_code == 503
    assert client.post("/api/v1/portfolio/simulate", json={}).status_code == 503


def test_invalid_covariance_is_reported(api: TestClient, monkeypatch) -> None:
    from app.analytics import monte_carlo

    def bad(*args, **kwargs):
        raise monte_carlo.SimulationInputError("invalid covariance matrix: not PSD")

    monkeypatch.setattr("app.services.simulation_service.simulate", bad)
    res = api.post("/api/v1/portfolio/simulate", json={"n_portfolios": 500, "seed": 99})
    assert res.status_code == 503 and "not PSD" in res.json()["message"]
