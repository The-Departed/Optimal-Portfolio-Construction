import numpy as np
import pandas as pd
import pytest

from app.analytics.efficient_frontier import non_dominated
from app.analytics.monte_carlo import (
    SimulationConfig,
    SimulationInputError,
    distribution_summary,
    simulate,
)
from app.analytics.portfolio_metrics import (
    InvalidWeightsError,
    portfolio_returns,
    portfolio_variances,
    sharpe_ratios,
    validate_weights,
)

LABELS = ["A", "B", "C"]
MU = pd.Series([0.10, 0.05, 0.02], index=LABELS)
COV = pd.DataFrame(
    [[0.04, 0.006, 0.0], [0.006, 0.01, 0.001], [0.0, 0.001, 0.0025]], index=LABELS, columns=LABELS
)


def test_hand_calculated_return_and_variance() -> None:
    w = np.array([[0.5, 0.3, 0.2]])
    assert portfolio_returns(w, MU.to_numpy())[0] == pytest.approx(
        0.5 * 0.10 + 0.3 * 0.05 + 0.2 * 0.02
    )
    manual = (
        0.25 * 0.04
        + 0.09 * 0.01
        + 0.04 * 0.0025
        + 2 * 0.5 * 0.3 * 0.006
        + 2 * 0.5 * 0.2 * 0.0
        + 2 * 0.3 * 0.2 * 0.001
    )
    assert portfolio_variances(w, COV.to_numpy())[0] == pytest.approx(manual)


@pytest.mark.parametrize(
    "w",
    [
        [[0.5, 0.6, -0.1]],
        [[1.2, -0.1, -0.1]],
        [[0.3, 0.3, 0.3]],
        [[np.nan, 0.5, 0.5]],
        [[0.5, 0.5]],
    ],
)
def test_invalid_weights_rejected(w: list) -> None:
    with pytest.raises(InvalidWeightsError):
        validate_weights(np.array(w), 3)


def test_sharpe_uses_risk_free_and_handles_zero_volatility() -> None:
    s = sharpe_ratios(np.array([0.10, 0.06]), np.array([0.2, 0.0]), 0.04)
    assert s[0] == pytest.approx(0.3)
    assert np.isnan(s[1])  # undefined, never inf


def test_simulation_constraints_and_independent_metrics() -> None:
    res = simulate(MU, COV, 0.03, SimulationConfig(n_portfolios=5_000, seed=7))
    w = res.weights
    assert w.shape == (5_000, 3)
    assert (w >= 0).all() and (w <= 1).all()
    np.testing.assert_allclose(w.sum(axis=1), 1.0, atol=1e-12)
    for i in (0, 123, 4_999):
        ret = sum(w[i, k] * MU.iloc[k] for k in range(3))
        var = sum(w[i, a] * COV.iloc[a, b] * w[i, b] for a in range(3) for b in range(3))
        assert res.expected_returns[i] == pytest.approx(ret, abs=1e-15)
        assert res.volatilities[i] == pytest.approx(var**0.5, abs=1e-15)
        assert res.sharpe[i] == pytest.approx((ret - 0.03) / var**0.5)
    assert res.volatilities[res.min_volatility_index] == res.volatilities.min()
    assert res.sharpe[res.max_sharpe_index] == np.nanmax(res.sharpe)


def test_same_seed_reproduces_and_different_seed_differs() -> None:
    a = simulate(MU, COV, 0.03, SimulationConfig(1_000, 11))
    b = simulate(MU, COV, 0.03, SimulationConfig(1_000, 11))
    c = simulate(MU, COV, 0.03, SimulationConfig(1_000, 12))
    np.testing.assert_array_equal(a.weights, b.weights)
    np.testing.assert_array_equal(a.sharpe, b.sharpe)
    assert not np.array_equal(a.weights, c.weights)


def test_covariance_order_must_match_expected_returns() -> None:
    shuffled = COV.loc[["B", "A", "C"], ["B", "A", "C"]]
    with pytest.raises(SimulationInputError, match="same asset order"):
        simulate(MU, shuffled, 0.03, SimulationConfig(100, 1))


def test_invalid_covariance_rejected() -> None:
    bad = COV.copy()
    bad.loc["A", "B"] = bad.loc["B", "A"] = 0.5  # implies |corr| > 1: not PSD
    with pytest.raises(SimulationInputError, match="positive semidefinite"):
        simulate(MU, bad, 0.03, SimulationConfig(100, 1))
    asym = COV.copy()
    asym.loc["A", "B"] = 0.0
    with pytest.raises(SimulationInputError, match="symmetric"):
        simulate(MU, asym, 0.03, SimulationConfig(100, 1))


@pytest.mark.parametrize(
    "config",
    [
        SimulationConfig(0, 1),
        SimulationConfig(300_000, 1),
        SimulationConfig(10, -1),
        SimulationConfig(10, 1, 0.0),
    ],
)
def test_parameters_validated(config: SimulationConfig) -> None:
    with pytest.raises(SimulationInputError):
        simulate(MU, COV, 0.03, config)


def test_empty_or_non_finite_inputs_rejected() -> None:
    one = MU.iloc[:1]
    with pytest.raises(SimulationInputError, match="two assets"):
        simulate(one, COV.loc[["A"], ["A"]], 0.03, SimulationConfig(10, 1))
    nan_mu = MU.copy()
    nan_mu["B"] = np.nan
    with pytest.raises(SimulationInputError, match="non-finite"):
        simulate(nan_mu, COV, 0.03, SimulationConfig(10, 1))
    with pytest.raises(SimulationInputError, match="risk-free"):
        simulate(MU, COV, float("nan"), SimulationConfig(10, 1))


def test_non_dominated_filter() -> None:
    rets = np.array([0.05, 0.08, 0.06, 0.10, 0.07])
    vols = np.array([0.10, 0.12, 0.15, 0.20, 0.12])
    # Index 2 is dominated by 1; index 4 by 1 (same vol, lower return).
    assert non_dominated(rets, vols).tolist() == [0, 1, 3]


def test_distribution_summary_ignores_undefined() -> None:
    s = distribution_summary(np.array([1.0, 2.0, np.nan, 3.0]))
    assert s["min"] == 1.0 and s["max"] == 3.0 and s["median"] == 2.0
