"""End-to-end validation on the real, validated dataset (no network). From backend/:

    uv run python -m scripts.validate_end_to_end

Drives the actual FastAPI application in-process through the full workflow (data
readiness -> analytics -> CAPM -> Monte Carlo -> three optimizations -> comparison and
error handling) and re-checks every financial result with independent calculations.
Exit code 0 only if every check passes.
"""

import sys

import numpy as np
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.assets import ASSET_IDS, EQUITY_IDS
from app.main import create_app

TOL = 1e-9
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, bool(ok), detail))
    return bool(ok)


def weights_ok(w: np.ndarray) -> bool:
    return abs(w.sum() - 1) <= TOL and bool((w >= -1e-12).all()) and bool((w <= 1 + 1e-12).all())


def main() -> int:
    client = TestClient(create_app(get_settings()))
    api = "/api/v1"

    # 1-2. Data readiness
    status = client.get(f"{api}/data/status").json()
    if not check(
        "data_ready",
        status.get("ready") is True,
        f"{status.get('state')} / {status.get('overall_status')}",
    ):
        return report()

    # 3. Returns and descriptive analytics
    summary = client.get(f"{api}/analytics/summary").json()
    check(
        "analytics_status", summary["status"] in ("PASS", "PASS_WITH_WARNINGS"), summary["status"]
    )
    fails = [c["name"] for c in summary["checks"] if c["status"] == "fail"]
    check(
        "analytics_checks",
        not fails,
        f"failed: {fails}" if fails else f"{len(summary['checks'])} checks, none failed",
    )
    cov = client.get(f"{api}/analytics/covariance").json()
    sigma = np.array(cov["values"])
    check(
        "covariance_psd",
        cov["diagnostics"]["positive_semidefinite"] and np.allclose(sigma, sigma.T),
        f"min eigenvalue {cov['diagnostics']['min_eigenvalue']:.3e}",
    )
    check("covariance_order", cov["labels"] == list(ASSET_IDS))

    # 4. CAPM
    capm = client.get(f"{api}/capm/summary").json()
    eq = capm["equities"]
    check(
        "capm_six_equities",
        [e["asset_id"] for e in eq] == list(EQUITY_IDS) and all(e["status"] == "ok" for e in eq),
    )
    rf, rm = capm["risk_free"]["annualized_rate"], capm["market"]["mean_return"]
    gaps = [abs(e["jensens_alpha"] - e["intercept_annualized"]) for e in eq]
    check(
        "capm_alpha_identity", max(gaps) < 1e-10, f"max |alpha - 252*intercept| = {max(gaps):.1e}"
    )
    capm_err = max(abs(e["capm_expected_return"] - (rf + e["beta"] * (rm - rf))) for e in eq)
    check("capm_expected_return_formula", capm_err < 1e-12, f"max error {capm_err:.1e}")
    check(
        "capm_same_sample",
        len({e["observations"] for e in eq}) == 1,
        f"{eq[0]['observations']} observations",
    )

    # 5. Monte Carlo: validity and reproducibility
    body = {"n_portfolios": 50_000, "seed": 42, "scatter_points": 2_000}
    sim = client.post(f"{api}/portfolio/simulate", json=body).json()
    sim2 = client.post(f"{api}/portfolio/simulate", json=body).json()
    check(
        "simulation_checks",
        all(c["status"] != "fail" for c in sim["checks"]),
        ", ".join(f"{c['name']}={c['status']}" for c in sim["checks"]),
    )
    check(
        "simulation_reproducible",
        sim["scatter"] == sim2["scatter"] and sim["candidates"] == sim2["candidates"],
    )
    mu = np.array([sim["inputs"]["expected_returns"][a] for a in ASSET_IDS])
    for c in sim["candidates"]:
        w = np.array([x["weight"] for x in c["weights"]])
        ok = (
            weights_ok(w)
            and abs(w @ mu - c["expected_return"]) < 1e-12
            and abs(np.sqrt(w @ sigma @ w) - c["volatility"]) < 1e-12
        )
        check(
            f"simulation_candidate_{c['label']}",
            ok,
            f"return {c['expected_return']:.4%}, vol {c['volatility']:.4%}",
        )

    # 6-8. Optimization for all three profiles, compared with Monte Carlo
    floor = None
    for payload in (
        {"profile": "conservative"},
        {"profile": "balanced"},
        {"profile": "growth", "max_volatility": 0.12},
    ):
        res = client.post(f"{api}/portfolio/optimize", json=payload)
        name = payload["profile"]
        if not check(f"optimize_{name}_http", res.status_code == 200, str(res.status_code)):
            continue
        o = res.json()
        w = np.array([x["weight"] for x in o["portfolio"]["weights"]])
        p = o["portfolio"]
        ret, vol = float(w @ mu), float(np.sqrt(w @ sigma @ w))
        sharpe = (ret - o["inputs"]["risk_free_rate"]) / vol
        ok = (
            weights_ok(w)
            and abs(ret - p["expected_return"]) < 1e-12
            and abs(vol - p["volatility"]) < 1e-10
            and abs(sharpe - p["sharpe_ratio"]) < 1e-8
            and o["solver"]["success"]
            and o["constraints"]["feasible"]
            and abs(o["inputs"]["risk_free_rate"] - sim["inputs"]["risk_free_rate"]) == 0
        )
        check(
            f"optimize_{name}_valid",
            ok,
            f"return {p['expected_return']:.4%}, vol {p['volatility']:.4%}, "
            f"Sharpe {p['sharpe_ratio']:.4f}",
        )
        c = o["comparison"]
        if name == "conservative":
            floor = p["volatility"]
            check(
                "conservative_not_worse_than_mc",
                c["volatility_difference"] <= 1e-12,
                f"vol diff {c['volatility_difference']:+.4%}",
            )
        elif name == "balanced":
            check(
                "balanced_not_worse_than_mc",
                c["sharpe_difference"] >= -1e-12,
                f"Sharpe diff {c['sharpe_difference']:+.4f}",
            )
        else:
            check(
                "growth_within_limit",
                p["volatility"] <= 0.12 + 1e-8,
                f"vol {p['volatility']:.10f} <= 0.12",
            )
            check(
                "growth_not_worse_than_mc",
                c["candidate"] is None or c["return_difference"] >= -1e-12,
                f"return diff {c['return_difference']:+.4%}",
            )

    # 10. Error handling
    if floor is not None:
        bad = client.post(
            f"{api}/portfolio/optimize",
            json={"profile": "growth", "max_volatility": round(floor / 2, 4)},
        )
        check(
            "growth_infeasible_reported",
            bad.status_code == 422 and bad.json()["code"] == "INFEASIBLE_CONSTRAINT",
            bad.json()["message"][:90],
        )
    missing = client.post(f"{api}/portfolio/optimize", json={"profile": "growth"})
    check(
        "growth_requires_limit",
        missing.status_code == 422 and missing.json()["code"] == "VALIDATION_ERROR",
    )
    too_many = client.post(f"{api}/portfolio/simulate", json={"n_portfolios": 10_000_000})
    check("simulation_size_limited", too_many.status_code == 422)
    frontier = client.get(f"{api}/portfolio/frontier").json()["points"]
    vols = [x["volatility"] for x in frontier]
    check(
        "frontier_starts_at_min_vol",
        floor is not None and abs(vols[0] - floor) < 1e-8,
        f"{len(frontier)} points",
    )
    return report()


def report() -> int:
    width = max(len(n) for n, _, _ in results)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<{width}}  {detail}")
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    print("END-TO-END: " + ("PASS" if not failed else f"FAIL ({', '.join(failed)})"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
