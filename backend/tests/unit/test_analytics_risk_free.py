import pandas as pd
import pytest

from app.analytics.risk_free import (
    UnsupportedYieldConventionError,
    check_units,
    infer_frequency,
    profile_risk_free,
)

UNITS = "percent per annum, actual/365, primary-auction implicit yield"


def _obs(values: list[float], step: int = 7) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "auction_date": pd.date_range("2018-12-19", periods=len(values), freq=f"{step}D"),
            "implicit_yield_pct": values,
        }
    )


def test_weekly_percent_series_profile() -> None:
    p = profile_risk_free(
        _obs([6.5, 6.6, 6.4, 6.55, 6.5, 6.45]),
        series_id="RF",
        units=UNITS,
        study_start=pd.Timestamp("2019-01-01"),
        proposed_conversion="pending",
    )
    assert p.units == "percent per annum" and p.day_count == "actual/365"
    assert p.frequency == "weekly" and p.median_gap_days == 7
    assert p.lookback_observations == 2 and p.observations == 4
    assert p.conversion_status == "pending_approval"


@pytest.mark.parametrize(
    ("gap", "freq"), [(1, "daily"), (7, "weekly"), (30, "monthly"), (14, "irregular")]
)
def test_frequency_inference(gap: float, freq: str) -> None:
    assert infer_frequency(gap) == freq


@pytest.mark.parametrize("units", ["decimal", "percent", "bps per annum", ""])
def test_ambiguous_units_rejected(units: str) -> None:
    with pytest.raises(UnsupportedYieldConventionError):
        check_units(units, pd.Series([6.5, 6.6]))


@pytest.mark.parametrize("values", [[0.065, 0.066], [98.4, 98.5]])
def test_values_inconsistent_with_percent_yields_rejected(values: list[float]) -> None:
    with pytest.raises(UnsupportedYieldConventionError):
        check_units("percent per annum", pd.Series(values))


def test_missing_day_count_and_duplicates_rejected() -> None:
    with pytest.raises(UnsupportedYieldConventionError, match="Day-count"):
        profile_risk_free(
            _obs([6.5] * 4),
            series_id="RF",
            units="percent per annum",
            study_start=pd.Timestamp("2019-01-01"),
            proposed_conversion="",
        )
    dup = _obs([6.5] * 4)
    dup.loc[1, "auction_date"] = dup.loc[0, "auction_date"]
    with pytest.raises(UnsupportedYieldConventionError, match="duplicate"):
        profile_risk_free(
            dup,
            series_id="RF",
            units=UNITS,
            study_start=pd.Timestamp("2019-01-01"),
            proposed_conversion="",
        )
