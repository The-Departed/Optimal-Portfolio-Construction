import numpy as np
import pandas as pd
import pytest

from app.analytics.returns import (
    NotAPriceSeriesError,
    max_return_discrepancy,
    returns_for,
    simple_returns,
)

DATES = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"])


def test_known_prices() -> None:
    r = simple_returns(pd.Series([100.0, 110.0, 99.0, 99.0], index=DATES))
    assert r.tolist() == pytest.approx([0.10, -0.10, 0.0])
    assert list(r.index) == list(DATES[1:])  # dates preserved, first observation dropped


def test_first_observation_is_undefined() -> None:
    r = simple_returns(pd.Series([100.0, 110.0, 121.0, 133.1], index=DATES), keep_first=True)
    assert np.isnan(r.iloc[0])
    assert np.isfinite(r.iloc[1:]).all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf])
def test_invalid_prices_raise_instead_of_becoming_zero(bad: float) -> None:
    with pytest.raises(ValueError):
        simple_returns(pd.Series([100.0, bad, 101.0, 102.0], index=DATES))


def test_unsorted_or_duplicate_dates_raise() -> None:
    with pytest.raises(ValueError, match="increasing"):
        simple_returns(pd.Series([1.0, 2.0, 3.0, 4.0], index=DATES[::-1]))
    with pytest.raises(ValueError, match="increasing"):
        simple_returns(pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-01", "2024-01-01"])))


def test_frame_returns_preserve_columns_and_alignment() -> None:
    prices = pd.DataFrame(
        {"A": [100.0, 101.0, 102.0, 103.0], "B": [50.0, 50.0, 49.0, 51.0]}, index=DATES
    )
    r = simple_returns(prices)
    assert list(r.columns) == ["A", "B"]
    assert r.loc["2024-01-04", "B"] == pytest.approx(51 / 49 - 1)


def test_yields_cannot_be_turned_into_price_returns() -> None:
    yields = pd.Series([6.5, 6.6, 6.4, 6.5], index=DATES)
    with pytest.raises(NotAPriceSeriesError):
        returns_for(yields, "yield")
    assert len(returns_for(pd.Series([1.0, 2.0, 3.0, 4.0], index=DATES), "nav")) == 3


def test_return_table_consistency_check() -> None:
    prices = pd.DataFrame({"A": [100.0, 110.0, 121.0, 133.1]}, index=DATES)
    good = simple_returns(prices)
    assert max_return_discrepancy(good, prices) == pytest.approx(0.0, abs=1e-15)
    tampered = good.copy()
    tampered.iloc[1, 0] += 0.01
    assert max_return_discrepancy(tampered, prices) == pytest.approx(0.01)
    with pytest.raises(ValueError, match="dates"):
        max_return_discrepancy(good.iloc[1:], prices)
