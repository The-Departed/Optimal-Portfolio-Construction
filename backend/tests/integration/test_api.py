from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"


def test_asset_universe(client: TestClient) -> None:
    body = client.get("/api/v1/assets").json()
    assert [a["id"] for a in body["assets"]][:1] == ["MM"]
    assert len(body["assets"]) == 8
    assert body["benchmark"]["id"] == "NIFTY50"
    assert body["risk_free"]["source"] == "RBI Handbook of Statistics"


def test_data_status_missing(client: TestClient) -> None:
    body = client.get("/api/v1/data/status").json()
    assert body["ready"] is False
    assert body["state"] == "missing"
    assert body["manifest_path"].endswith("processed/manifest.json")
    assert not body["manifest_path"].startswith("/")


def test_data_status_invalid_manifest(client: TestClient, write_manifest) -> None:
    write_manifest("{not json")
    body = client.get("/api/v1/data/status").json()
    assert body["ready"] is False
    assert body["state"] == "invalid"


def test_data_status_blocked(client: TestClient, write_artifacts) -> None:
    write_artifacts("BLOCKED")
    body = client.get("/api/v1/data/status").json()
    assert body["state"] == "validation_failed"
    assert body["ready"] is False
    assert body["overall_status"] == "BLOCKED"
    assert body["critical_failures"]
    assert body["datasets"][0]["failures"] == ["coverage: x"]


def test_data_status_ready(client: TestClient, write_artifacts) -> None:
    write_artifacts("PASS_WITH_WARNINGS")
    body = client.get("/api/v1/data/status").json()
    assert body["ready"] is True
    assert body["state"] == "ready"
    assert body["overall_status"] == "PASS_WITH_WARNINGS"
    assert body["common_period"]["return_observations"] == 9
    assert body["datasets"][0]["dataset_id"] == "GSEC"


def test_manifest_without_summary_is_not_ready(client: TestClient, write_manifest) -> None:
    write_manifest(
        {"generated_at": "2026-01-01T00:00:00", "validation_passed": True, "overall_status": "PASS"}
    )
    body = client.get("/api/v1/data/status").json()
    assert body["ready"] is False
    assert body["state"] == "invalid"


def test_inconsistent_manifest_and_summary_is_not_ready(
    client: TestClient, write_artifacts, data_dir
) -> None:
    write_artifacts("PASS")
    path = data_dir / "processed" / "manifest.json"
    path.write_text(path.read_text().replace('"PASS"', '"BLOCKED"'))
    assert client.get("/api/v1/data/status").json()["state"] == "invalid"


def test_analyses_report_data_not_ready(client: TestClient) -> None:
    for method, url, payload in [
        ("get", "/api/v1/capm/summary", None),
        ("post", "/api/v1/portfolio/simulate", {}),
        ("post", "/api/v1/portfolio/optimize", {"profile": "balanced"}),
    ]:
        response = client.request(method, url, json=payload)
        assert response.status_code == 503, url
        assert response.json()["code"] == "DATA_NOT_READY"


def test_analyses_refuse_ready_manifest_without_processed_files(
    client: TestClient, write_artifacts
) -> None:
    # Phase 6 replaced the Phase 1 "not implemented" placeholder; a manifest that claims
    # readiness without the processed files must still never yield a result.
    write_artifacts("PASS")
    for method, url, payload in [
        ("post", "/api/v1/portfolio/optimize", {"profile": "conservative"}),
        ("post", "/api/v1/portfolio/simulate", {}),
        ("get", "/api/v1/capm/summary", None),
    ]:
        response = client.request(method, url, json=payload)
        assert response.status_code == 503, url
        assert response.json()["code"] == "DATA_NOT_READY"
        assert "data pipeline" in response.json()["message"]


def test_optimize_validation_error_shape(client: TestClient) -> None:
    response = client.post("/api/v1/portfolio/optimize", json={"profile": "growth"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["errors"]


def test_unknown_profile_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/portfolio/optimize", json={"profile": "aggressive"})
    assert response.status_code == 422


def test_profiles(client: TestClient) -> None:
    body = client.get("/api/v1/portfolio/profiles").json()
    assert [p["profile"] for p in body] == ["conservative", "balanced", "growth"]
    assert [p["requires_max_volatility"] for p in body] == [False, False, True]
