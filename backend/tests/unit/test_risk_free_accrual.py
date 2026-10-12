import pandas as pd
import pytest

from app.analytics.risk_free import RiskFreeAlignmentError, accrued_risk_free

AUCTIONS = pd.DataFrame(
    {
        "auction_date": pd.to_datetime(["2024-01-03", "2024-01-10", "2024-01-17"]),
        "implicit_yield_pct": [6.5, 7.3, 6.0],
    }
)


def _intervals(dates: list[str]) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    return idx[:-1], idx[1:]


def test_as_of_yield_known_at_interval_start_and_calendar_day_accrual() -> None:
    starts, ends = _intervals(["2024-01-05", "2024-01-08", "2024-01-10", "2024-01-11"])
    out = accrued_risk_free(starts, ends, AUCTIONS)
    # Fri 5 -> Mon 8: 3 calendar days at the 3 Jan yield.
    assert out["calendar_days"].tolist() == [3, 2, 1]
    assert out["rf"].iloc[0] == pytest.approx(0.065 * 3 / 365)
    # Interval (8, 10]: the 10 Jan auction is not yet known at the start (8 Jan).
    assert out["yield_pct"].iloc[1] == 6.5
    # Interval (10, 11]: the 10 Jan auction is known at the start.
    assert out["yield_pct"].iloc[2] == 7.3
    assert list(out.index) == list(ends)


def test_no_prior_auction_or_stale_yield_raises() -> None:
    starts, ends = _intervals(["2024-01-01", "2024-01-02"])
    with pytest.raises(RiskFreeAlignmentError, match="no auction"):
        accrued_risk_free(starts, ends, AUCTIONS)
    starts, ends = _intervals(["2024-03-01", "2024-03-04"])
    with pytest.raises(RiskFreeAlignmentError, match="days old"):
        accrued_risk_free(starts, ends, AUCTIONS, max_staleness_days=35)


def test_missing_yields_and_bad_intervals_raise() -> None:
    bad = AUCTIONS.copy()
    bad.loc[1, "implicit_yield_pct"] = float("nan")
    starts, ends = _intervals(["2024-01-05", "2024-01-08"])
    with pytest.raises(RiskFreeAlignmentError, match="missing"):
        accrued_risk_free(starts, ends, bad)
    with pytest.raises(RiskFreeAlignmentError, match="after it starts"):
        accrued_risk_free(ends, starts, AUCTIONS)
