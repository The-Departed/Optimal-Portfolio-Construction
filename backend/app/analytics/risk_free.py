"""Inspection of the risk-free yield series (no conversion is applied in Phase 3).

The series is a quoted annual yield, not a price: it must never pass through the
price-return formula, and its daily conversion awaits an approved convention.
"""

from dataclasses import dataclass

import pandas as pd

SUPPORTED_UNITS = "percent per annum"
SUPPORTED_DAY_COUNT = "actual/365"


class UnsupportedYieldConventionError(ValueError):
    """The yield metadata or values do not match a supported, unambiguous convention."""


@dataclass(frozen=True, slots=True)
class RiskFreeProfile:
    series_id: str
    measure: str
    units: str
    day_count: str
    frequency: str
    observations: int
    first_date: str
    last_date: str
    lookback_observations: int
    median_gap_days: float
    max_gap_days: int
    min_yield_pct: float
    max_yield_pct: float
    mean_yield_pct: float
    conversion_status: str
    proposed_conversion: str
    limitations: tuple[str, ...]


def infer_frequency(median_gap_days: float) -> str:
    if median_gap_days <= 1.5:
        return "daily"
    if 6 <= median_gap_days <= 8:
        return "weekly"
    if 27 <= median_gap_days <= 32:
        return "monthly"
    return "irregular"


def check_units(units: str, values_pct: pd.Series) -> None:
    """Accept only an explicitly percent-per-annum series whose values look like percents."""
    if "percent" not in units.lower() or "per annum" not in units.lower():
        raise UnsupportedYieldConventionError(
            f"Unsupported or ambiguous yield units {units!r}; expected '{SUPPORTED_UNITS}'"
        )
    median = float(values_pct.median())
    if not 0.5 <= median <= 20.0:
        raise UnsupportedYieldConventionError(
            f"Median value {median} is inconsistent with an annual yield in percent "
            "(decimal fraction or price?)"
        )


def profile_risk_free(
    observations: pd.DataFrame,
    *,
    series_id: str,
    units: str,
    study_start: pd.Timestamp,
    proposed_conversion: str,
    limitations: tuple[str, ...] = (),
) -> RiskFreeProfile:
    """Describe the native-frequency auction series.

    ``observations`` has ``auction_date`` and ``implicit_yield_pct`` columns.
    """
    if "actual/365" not in units:
        raise UnsupportedYieldConventionError(f"Day-count convention missing from units {units!r}")
    df = observations.sort_values("auction_date")
    dates = pd.DatetimeIndex(df["auction_date"])
    if dates.has_duplicates:
        raise UnsupportedYieldConventionError("duplicate auction dates")
    values = df["implicit_yield_pct"].astype("float64")
    check_units(units, values)
    gaps = pd.Series(dates[1:] - dates[:-1]).dt.days
    median_gap = float(gaps.median())
    in_period = dates >= study_start
    return RiskFreeProfile(
        series_id=series_id,
        measure="primary-auction implicit yield at cut-off price (91-day T-bill)",
        units=SUPPORTED_UNITS,
        day_count=SUPPORTED_DAY_COUNT,
        frequency=infer_frequency(median_gap),
        observations=int(in_period.sum()),
        first_date=dates[in_period][0].date().isoformat(),
        last_date=dates[-1].date().isoformat(),
        lookback_observations=int((~in_period).sum()),
        median_gap_days=median_gap,
        max_gap_days=int(gaps.max()),
        min_yield_pct=float(values[in_period].min()),
        max_yield_pct=float(values[in_period].max()),
        mean_yield_pct=float(values[in_period].mean()),
        conversion_status="pending_approval",
        proposed_conversion=proposed_conversion,
        limitations=limitations,
    )
