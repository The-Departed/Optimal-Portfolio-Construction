import numpy as np
import pandas as pd
import pytest

from app.analytics import capm
from app.services.capm_service import DEFINITIONS

IDX = pd.bdate_range("2023-01-02", periods=300)


def _series(values: np.ndarray) -> pd.Series:
    return pd.Series(values, index=IDX[: len(values)])


def _known(
    beta: float = 1.3,
    alpha: float = 2e-4,
    rf_level: float = 2e-4,
    noise: float = 1e-5,
    n: int = 300,
):
    rng = np.random.default_rng(0)
    rf = _series(rf_level + 1e-4 * np.sin(np.arange(n) / 10))  # time-varying risk-free
    market = _series(rng.normal(5e-4, 0.01, n))
    asset = rf + alpha + beta * (market - rf) + _series(rng.normal(0, noise, n))
    return asset, market, rf


def test_recovers_known_linear_relationship() -> None:
    asset, market, rf = _known()
    reg = capm.fit(capm.build_sample(asset, market, rf))
    assert reg.beta == pytest.approx(1.3, abs=1e-3)
    assert reg.intercept_daily == pytest.approx(2e-4, abs=1e-5)
    assert reg.r_squared > 0.99 and reg.beta_ci_low < 1.3 < reg.beta_ci_high


def test_beta_uses_excess_not_raw_returns() -> None:
    # A risk-free rate that co-moves with the market separates the two regressions:
    # raw slope = beta + 0.3 (1 - beta) = 1.35, excess-return beta = 1.5.
    rng = np.random.default_rng(3)
    market = _series(rng.normal(5e-4, 0.01, 300))
    rf = 0.002 + 0.3 * market
    asset = rf + 1e-4 + 1.5 * (market - rf) + _series(rng.normal(0, 1e-5, 300))
    reg = capm.fit(capm.build_sample(asset, market, rf))
    raw_slope = np.polyfit(market.to_numpy(), asset.to_numpy(), 1)[0]
    assert reg.beta == pytest.approx(1.5, abs=1e-3)
    assert raw_slope == pytest.approx(1.35, abs=1e-3)


def test_dates_must_be_aligned_and_complete() -> None:
    asset, market, rf = _known()
    with pytest.raises(capm.CapmEstimationError, match="identical dates"):
        capm.build_sample(asset.iloc[1:], market, rf)
    gappy = asset.copy()
    gappy.iloc[5] = np.nan
    with pytest.raises(capm.CapmEstimationError, match="missing"):
        capm.build_sample(gappy, market, rf)
    sample = capm.build_sample(asset, market, rf)
    assert sample.index.equals(asset.index)
    np.testing.assert_allclose(sample["asset_excess"], asset - rf)


def test_constant_market_excess_is_rejected() -> None:
    rf = _series(np.full(100, 1e-4))
    market = rf + 0.001
    asset = _series(np.random.default_rng(1).normal(0, 0.01, 100))
    with pytest.raises(capm.CapmEstimationError, match="constant"):
        capm.fit(capm.build_sample(asset, market, rf))


def test_insufficient_sample_is_rejected() -> None:
    asset, market, rf = _known(n=30)
    with pytest.raises(capm.CapmEstimationError, match="at least 60"):
        capm.fit(capm.build_sample(asset, market, rf))


def test_annualization_is_consistent_and_alpha_identity_holds() -> None:
    asset, market, rf = _known()
    ev = capm.evaluate("X", capm.build_sample(asset, market, rf), periods_per_year=252)
    assert ev.risk_free_annual == pytest.approx(rf.mean() * 252)
    assert ev.market_mean_return == pytest.approx(market.mean() * 252)
    assert ev.historical_mean_return == pytest.approx(asset.mean() * 252)
    expected = ev.risk_free_annual + ev.regression.beta * (
        ev.market_mean_return - ev.risk_free_annual
    )
    assert ev.capm_expected_return == pytest.approx(expected)
    assert ev.jensens_alpha == pytest.approx(ev.historical_mean_return - ev.capm_expected_return)
    assert ev.jensens_alpha == pytest.approx(ev.intercept_annualized, abs=1e-12)  # OLS identity


def test_expected_return_formula() -> None:
    assert capm.capm_expected_return(1.2, 0.05, 0.12) == pytest.approx(0.134)
    assert capm.capm_expected_return(0.0, 0.05, 0.12) == pytest.approx(0.05)


def test_intercept_units_are_documented() -> None:
    assert "per trading interval" in DEFINITIONS["intercept_daily"]
    assert "annualized" in DEFINITIONS["jensens_alpha"]


def test_newey_west_lags() -> None:
    assert capm.newey_west_lags(100) == 4
    assert capm.newey_west_lags(1689) == 7
