import math

import numpy as np
import pandas as pd
import pytest

from app.analytics.conventions import Conventions
from app.analytics.statistics import annualized_return, describe, histogram


def _series(values: list[float], start: str = "2024-01-02") -> pd.Series:
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)))


def _prices_from(returns: pd.Series, p0: float = 100.0) -> pd.Series:
    path = p0 * np.cumprod(np.r_[1.0, 1.0 + returns.to_numpy()])
    index = returns.index.insert(0, returns.index[0] - pd.offsets.BDay(1))
    return pd.Series(path, index=index)


def _g1(x: np.ndarray) -> float:
    """Independent implementation of the adjusted Fisher-Pearson skewness G1."""
    n, m = len(x), x.mean()
    m2, m3 = ((x - m) ** 2).mean(), ((x - m) ** 3).mean()
    return math.sqrt(n * (n - 1)) / (n - 2) * m3 / m2**1.5


def _g2(x: np.ndarray) -> float:
    """Independent implementation of sample excess kurtosis G2."""
    n, m = len(x), x.mean()
    m2, m4 = ((x - m) ** 2).mean(), ((x - m) ** 4).mean()
    g2 = m4 / m2**2 - 3
    return (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * g2 + 6)


def test_moments_match_hand_calculations() -> None:
    values = [0.01, -0.02, 0.03, 0.0, 0.015, -0.005]
    r = _series(values)
    s = describe("X", r)
    x = np.array(values)
    assert s.observations == 6
    assert s.mean_daily == pytest.approx(sum(values) / 6)
    assert s.median_daily == pytest.approx((0.01 + 0.0) / 2)
    assert s.std_daily == pytest.approx(math.sqrt(((x - x.mean()) ** 2).sum() / 5))  # ddof = 1
    assert (s.min_daily, s.max_daily) == (-0.02, 0.03)
    assert s.skewness == pytest.approx(_g1(x))
    assert s.excess_kurtosis == pytest.approx(_g2(x))
    assert s.annualized_volatility == pytest.approx(s.std_daily * math.sqrt(252))
    assert s.annualized_mean_return == pytest.approx(s.mean_daily * 252)


def test_symmetric_sample_has_zero_skew() -> None:
    s = describe("X", _series([-0.02, -0.01, 0.0, 0.01, 0.02]))
    assert s.skewness == pytest.approx(0.0, abs=1e-12)


def test_cumulative_and_compound_annual_return() -> None:
    prices = pd.Series(
        [100.0, 110.0, 121.0], index=pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01"])
    )
    r = prices / prices.shift(1) - 1
    s = describe("X", r.iloc[1:], prices)
    assert s.cumulative_return == pytest.approx(0.21)
    days = (pd.Timestamp("2022-01-01") - pd.Timestamp("2020-01-01")).days  # 731
    assert s.elapsed_calendar_days == days
    assert s.annualized_return == pytest.approx(1.21 ** (365.25 / days) - 1)
    # CAGR differs from the arithmetic annualization of the mean daily return.
    assert s.annualized_return != pytest.approx(s.annualized_mean_return)


def test_short_interval_is_not_annualized() -> None:
    r = _series([0.01, 0.02, -0.01])
    value, days, reason = annualized_return(_prices_from(r), Conventions())
    assert value is None and days < 365 and "not annualized" in reason
    s = describe("X", r, _prices_from(r))
    assert s.annualized_return is None and s.cumulative_return is not None
    assert any("not annualized" in n for n in s.notes)


def test_insufficient_observations() -> None:
    s = describe("X", _series([0.01]))
    assert s.std_daily is None and s.annualized_volatility is None
    assert s.skewness is None and s.excess_kurtosis is None
    assert s.notes


def test_constant_returns_have_undefined_shape() -> None:
    s = describe("X", _series([0.001] * 10))
    assert s.std_daily == 0.0
    assert s.skewness is None and s.excess_kurtosis is None
    assert any("constant" in n for n in s.notes)


def test_missing_returns_are_rejected_not_zero_filled() -> None:
    with pytest.raises(ValueError, match="missing"):
        describe("X", _series([0.01, np.nan, 0.02]))


def test_price_path_must_match_returns() -> None:
    r = _series([0.01, 0.02, 0.03])
    with pytest.raises(ValueError, match="price path"):
        describe("X", r, _prices_from(r).iloc[1:])


def test_histogram_counts_every_observation() -> None:
    r = _series(list(np.linspace(-0.05, 0.05, 101)))
    counts, edges = histogram(r, 10)
    assert counts.sum() == 101 and len(edges) == 11
