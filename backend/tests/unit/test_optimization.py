"""Constrained optimizer on SYNTHETIC fixtures with analytically or exhaustively known answers."""

import itertools

import numpy as np
import pytest

from app.analytics import optimization as opt

LABELS = ["A", "B", "C"]
MU = np.array([0.12, 0.07, 0.03])
COV = np.array([[0.09, 0.012, 0.0], [0.012, 0.0225, 0.001], [0.0, 0.001, 0.0016]])
RF = 0.02


def _grid(step: float = 0.01) -> np.ndarray:
    k = round(1 / step)
    pts = [(i, j, k - i - j) for i, j in itertools.product(range(k + 1), repeat=2) if i + j <= k]
    return np.array(pts, dtype=float) / k


def _feasible(w: np.ndarray) -> None:
    assert abs(w.sum() - 1) < 1e-10
    assert (w >= 0).all() and (w <= 1).all()


def test_two_asset_minimum_variance_matches_closed_form() -> None:
    mu, cov = MU[:2], COV[:2, :2]
    s1, s2, s12 = cov[0, 0], cov[1, 1], cov[0, 1]
    w1 = (s2 - s12) / (s1 + s2 - 2 * s12)
    sol = opt.minimize_volatility(mu, cov, RF)
    np.testing.assert_allclose(sol.weights, [w1, 1 - w1], atol=1e-7)
    _feasible(sol.weights)


def test_minimum_volatility_beats_exhaustive_grid() -> None:
    sol = opt.minimize_volatility(MU, COV, RF)
    grid = _grid()
    grid_vol = np.sqrt(np.einsum("ij,jk,ik->i", grid, COV, grid)).min()
    assert sol.volatility <= grid_vol + 1e-12
    _feasible(sol.weights)
    assert sol.volatility == pytest.approx(np.sqrt(sol.weights @ COV @ sol.weights))
    assert sol.expected_return == pytest.approx(sol.weights @ MU)


def test_maximum_sharpe_beats_grid_and_methods_agree() -> None:
    sol = opt.maximize_sharpe(MU, COV, RF)
    grid = _grid()
    vols = np.sqrt(np.einsum("ij,jk,ik->i", grid, COV, grid))
    best_grid = ((grid @ MU - RF) / vols).max()
    assert sol.sharpe >= best_grid - 1e-12
    assert sol.sharpe == pytest.approx((sol.expected_return - RF) / sol.volatility)
    assert sol.verification["convex_vs_direct_sharpe_gap"] < 1e-7
    _feasible(sol.weights)


def test_growth_respects_binding_limit_and_beats_grid() -> None:
    limit = 0.10
    sol = opt.maximize_return(MU, COV, RF, limit)
    assert sol.volatility <= limit + 1e-8
    grid = _grid()
    vols = np.sqrt(np.einsum("ij,jk,ik->i", grid, COV, grid))
    assert sol.expected_return >= (grid @ MU)[vols <= limit].max() - 1e-12
    assert sol.volatility_slack is not None and abs(sol.volatility_slack) < 1e-6  # binding
    _feasible(sol.weights)


def test_growth_with_loose_limit_holds_highest_return_asset() -> None:
    sol = opt.maximize_return(MU, COV, RF, 0.5)
    np.testing.assert_allclose(sol.weights, [1, 0, 0], atol=1e-7)
    assert sol.volatility_slack == pytest.approx(0.5 - 0.3, abs=1e-7)


def test_infeasible_volatility_limit_is_reported() -> None:
    floor = opt.minimize_volatility(MU, COV, RF).volatility
    with pytest.raises(opt.InfeasibleProblemError) as info:
        opt.maximize_return(MU, COV, RF, floor * 0.5)
    assert info.value.minimum_volatility == pytest.approx(floor)


@pytest.mark.parametrize("limit", [0.0, -0.1, float("inf"), float("nan")])
def test_invalid_volatility_limit(limit: float) -> None:
    with pytest.raises(opt.OptimizationInputError):
        opt.maximize_return(MU, COV, RF, limit)


def test_invalid_inputs_rejected() -> None:
    with pytest.raises(opt.OptimizationInputError, match="non-finite"):
        opt.validate_inputs(np.array([0.1, np.nan, 0.03]), COV, RF, LABELS)
    with pytest.raises(opt.OptimizationInputError, match="expected 3"):
        opt.validate_inputs(MU[:2], COV, RF, LABELS)
    bad = COV.copy()
    bad[0, 1] = bad[1, 0] = 0.2  # |corr| > 1: not PSD
    with pytest.raises(opt.OptimizationInputError, match="positive semidefinite"):
        opt.validate_inputs(MU, bad, RF, LABELS)
    with pytest.raises(opt.OptimizationInputError, match="risk-free"):
        opt.validate_inputs(MU, COV, float("nan"), LABELS)


def test_sharpe_undefined_when_no_asset_beats_risk_free() -> None:
    with pytest.raises(opt.InfeasibleProblemError):
        opt.maximize_sharpe(MU, COV, 0.5)


def test_solver_failure_is_never_reported_as_success(monkeypatch) -> None:
    from scipy.optimize import OptimizeResult

    def failing(fun, x0, **kwargs):
        return OptimizeResult(
            x=x0 * 0.9,
            success=False,
            message="Iteration limit reached",
            nit=1000,
            nfev=5000,
            fun=1.0,
        )

    monkeypatch.setattr(opt, "minimize", failing)
    with pytest.raises(opt.SolverFailedError) as info:
        opt.minimize_volatility(MU, COV, RF)
    assert info.value.attempts and not any(a.accepted for a in info.value.attempts)


def test_infeasible_solver_output_is_rejected(monkeypatch) -> None:
    from scipy.optimize import OptimizeResult

    def lying(fun, x0, **kwargs):  # claims success but weights sum to 1.2
        return OptimizeResult(
            x=np.full(len(x0), 0.4), success=True, message="ok", nit=3, nfev=9, fun=0.0
        )

    monkeypatch.setattr(opt, "minimize", lying)
    with pytest.raises(opt.SolverFailedError):
        opt.minimize_volatility(MU, COV, RF)


def test_efficient_frontier_is_monotone() -> None:
    pts = opt.efficient_frontier(MU, COV, RF, 12)
    rets = [p[0] for p in pts]
    vols = [p[1] for p in pts]
    assert vols[0] == pytest.approx(opt.minimize_volatility(MU, COV, RF).volatility)
    assert all(np.diff(rets) > 0) and all(np.diff(vols) >= -1e-10)
    assert rets[-1] == pytest.approx(MU.max())
    for _, _, w in pts:
        _feasible(w)
