import pandas as pd
import pytest

from app.data_pipeline.alignment import align, reference_calendar
from app.data_pipeline.returns import sessions_spanned, simple_returns


def _s(dates: list[str], values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.to_datetime(dates))


def test_simple_returns() -> None:
    r = simple_returns(_s(["2024-01-01", "2024-01-02", "2024-01-03"], [100.0, 110.0, 99.0]))
    assert r.round(10).tolist() == [0.1, -0.1]
    assert r.index[0] == pd.Timestamp("2024-01-02")  # first observation has no return


def test_simple_returns_refuse_gaps() -> None:
    with pytest.raises(ValueError):
        simple_returns(_s(["2024-01-01", "2024-01-02"], [100.0, float("nan")]))


def test_sessions_spanned() -> None:
    cal = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"])
    spans = sessions_spanned(pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-04"]), cal)
    assert spans.tolist() == [1, 2]


def test_alignment_uses_intersection_and_never_fills() -> None:
    days = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
    cal = reference_calendar(
        {"A": _s(days, [1, 2, 3, 4])}, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31")
    )
    a = _s(days, [100, 101, 102, 103])
    b = _s(["2024-01-01", "2024-01-02", "2024-01-04"], [50, 51, 53])  # missing Jan 3
    bench = _s(days, [1000, 1001, 1002, 1003])
    out = align({"A": a, "B": b}, ("IDX", bench), cal)
    assert list(out.common_dates.strftime("%Y-%m-%d")) == ["2024-01-01", "2024-01-02", "2024-01-04"]
    assert not out.portfolio_prices.isna().any().any()
    assert list(out.portfolio_prices.columns) == ["A", "B"]
    assert out.portfolio_returns.loc["2024-01-04", "A"] == pytest.approx(103 / 101 - 1)
    assert out.multi_session_returns.to_dict() == {pd.Timestamp("2024-01-04"): 2}
    assert out.excluded_sessions["B"] == [pd.Timestamp("2024-01-03")]


def test_alignment_is_repeatable() -> None:
    days = ["2024-01-01", "2024-01-02", "2024-01-03"]
    cal = pd.to_datetime(days)
    args = ({"A": _s(days, [1.0, 2.0, 3.0])}, ("IDX", _s(days, [1.0, 1.1, 1.2])), cal)
    pd.testing.assert_frame_equal(align(*args).portfolio_returns, align(*args).portfolio_returns)
