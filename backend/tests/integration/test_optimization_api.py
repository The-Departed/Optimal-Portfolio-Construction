"""Optimization endpoints on a SYNTHETIC validated dataset (Phase 2 pipeline)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.assets import ASSET_IDS
from app.main import create_app
from app.services import analytics_service, simulation_service

SIM = {"simulation_portfolios": 2_000, "simulation_seed": 5}


@pytest.fixture
def api(analytics_settings: Settings) -> TestClient:
    analytics_service.clear_cache()
    simulation_service.clear_cache()
    return TestClient(create_app(analytics_settings))


def _post(api: TestClient, **body) -> dict:
    res = api.post("/api/v1/portfolio/optimize", json={**SIM, **body})
    assert res.status_code == 200, res.text
    return res.json()


def _check_portfolio(body: dict) -> np.ndarray:
    assert body["status"] == "optimal" and body["solver"]["success"]
    assert body["constraints"]["feasible"]
    w = np.array([x["weight"] for x in body["portfolio"]["weights"]])
    assert [x["asset_id"] for x in body["portfolio"]["weights"]] == list(ASSET_IDS)
    assert abs(w.sum() - 1) < 1e-9 and (w >= 0).all() and (w <= 1).all()
    mu = np.array([body["inputs"]["expected_returns"][a] for a in ASSET_IDS])
    assert body["portfolio"]["expected_return"] == pytest.approx(w @ mu, abs=1e-12)
    rf = body["inputs"]["risk_free_rate"]
    p = body["portfolio"]
    assert p["sharpe_ratio"] == pytest.approx((p["expected_return"] - rf) / p["volatility"])
    return w


def test_conservative_beats_or_matches_simulation(api: TestClient) -> None:
    body = _post(api, profile="conservative")
    _check_portfolio(body)
    c = body["comparison"]
    assert c["candidate"] is not None and c["candidate_satisfies_constraints"]
    assert c["volatility_difference"] <= 1e-12
    assert body["portfolio"]["volatility"] == pytest.approx(
        c["candidate"]["volatility"] + c["volatility_difference"]
    )


def test_balanced_beats_or_matches_simulation(api: TestClient) -> None:
    body = _post(api, profile="balanced")
    _check_portfolio(body)
    assert body["comparison"]["sharpe_difference"] >= -1e-12
    assert body["solver"]["starts_accepted"] >= 1
    assert any(a["label"] == "monte_carlo_max_sharpe" for a in body["solver"]["attempts"])


def test_growth_respects_user_limit(api: TestClient) -> None:
    floor = _post(api, profile="conservative")["portfolio"]["volatility"]
    limit = round(floor * 1.5, 4)
    body = _post(api, profile="growth", max_volatility=limit)
    _check_portfolio(body)
    assert body["portfolio"]["volatility"] <= limit + 1e-8
    assert body["max_volatility"] == limit and body["constraints"]["volatility_limit"] == limit
    c = body["comparison"]
    if c["candidate"] is not None:
        assert c["candidate"]["volatility"] <= limit
        assert c["return_difference"] >= -1e-12


def test_growth_infeasible_limit(api: TestClient) -> None:
    res = api.post(
        "/api/v1/portfolio/optimize", json={**SIM, "profile": "growth", "max_volatility": 0.0001}
    )
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "INFEASIBLE_CONSTRAINT"
    assert body["details"]["minimum_volatility"] > 0.0001


def test_growth_without_simulated_candidate(api: TestClient) -> None:
    floor = _post(api, profile="conservative")["portfolio"]["volatility"]
    body = _post(api, profile="growth", max_volatility=round(floor * 1.0001, 6))
    # Random samples essentially never sit this close to the minimum-variance portfolio.
    assert body["comparison"]["candidate"] is None
    assert "No simulated portfolio" in body["comparison"]["note"]


def test_solver_failure_is_reported(api: TestClient, monkeypatch) -> None:
    from app.analytics import optimization as opt

    def fail(*args, **kwargs):
        raise opt.SolverFailedError("synthetic failure", [])

    monkeypatch.setattr(opt, "minimize_volatility", fail)
    res = api.post("/api/v1/portfolio/optimize", json={**SIM, "profile": "conservative"})
    assert res.status_code == 422 and res.json()["code"] == "OPTIMIZATION_FAILED"


@pytest.mark.parametrize(
    "payload",
    [
        {"profile": "growth"},
        {"profile": "balanced", "max_volatility": 0.1},
        {"profile": "growth", "max_volatility": -0.1},
        {"profile": "aggressive"},
        {"profile": "balanced", "simulation_portfolios": 10},
    ],
)
def test_validation(api: TestClient, payload: dict) -> None:
    res = api.post("/api/v1/portfolio/optimize", json=payload)
    assert res.status_code == 422 and res.json()["code"] == "VALIDATION_ERROR"


def test_frontier(api: TestClient) -> None:
    body = api.get("/api/v1/portfolio/frontier", params={"points": 8}).json()
    vols = [p["volatility"] for p in body["points"]]
    rets = [p["expected_return"] for p in body["points"]]
    assert len(body["points"]) >= 2 and body["asset_order"] == list(ASSET_IDS)
    assert all(np.diff(rets) > 0) and all(np.diff(vols) >= -1e-10)
    for p in body["points"]:
        assert abs(sum(p["weights"]) - 1) < 1e-9 and min(p["weights"]) >= 0
    assert api.get("/api/v1/portfolio/frontier", params={"points": 1}).status_code == 422


def test_unavailable_without_data(settings: Settings) -> None:
    analytics_service.clear_cache()
    client = TestClient(create_app(settings))
    assert (
        client.post("/api/v1/portfolio/optimize", json={"profile": "balanced"}).status_code == 503
    )
    assert client.get("/api/v1/portfolio/frontier").status_code == 503
