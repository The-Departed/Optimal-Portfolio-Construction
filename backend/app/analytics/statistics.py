"""Descriptive statistics for daily return series.

All inputs are complete (no NaN) return series; statistics that cannot be estimated
from the available data are returned as ``None`` with a reason, never as zero.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from app.analytics.conventions import DEFAULT_CONVENTIONS, Conventions


@dataclass(frozen=True, slots=True)
class DescriptiveStatistics:
    series_id: str
    observations: int
    start: str
    end: str
    mean_daily: float | None
    median_daily: float | None
    std_daily: float | None
    min_daily: float | None
    max_daily: float | None
    skewness: float | None
    excess_kurtosis: float | None
    cumulative_return: float | None
    annualized_return: float | None
    annualized_mean_return: float | None
    annualized_volatility: float | None
    elapsed_calendar_days: int | None
    notes: tuple[str, ...] = field(default_factory=tuple)


def cumulative_return(prices: pd.Series) -> float:
    return float(prices.iloc[-1] / prices.iloc[0] - 1.0)


def annualized_return(
    prices: pd.Series, conventions: Conventions = DEFAULT_CONVENTIONS
) -> tuple[float | None, int, str | None]:
    """CAGR by elapsed calendar time: (P_end/P_start)^(365.25/days) - 1.

    Returns ``(value, elapsed_days, reason)``; ``value`` is None when the interval is
    shorter than ``min_annualization_days``.
    """
    days = int((prices.index[-1] - prices.index[0]).days)
    if days < conventions.min_annualization_days:
        return (
            None,
            days,
            (
                f"interval of {days} calendar days is shorter than "
                f"{conventions.min_annualization_days}; not annualized"
            ),
        )
    growth = prices.iloc[-1] / prices.iloc[0]
    return float(growth ** (conventions.calendar_days_per_year / days) - 1.0), days, None


def annualized_volatility(
    std_daily: float, conventions: Conventions = DEFAULT_CONVENTIONS
) -> float:
    return std_daily * math.sqrt(conventions.periods_per_year)


def describe(
    series_id: str,
    returns: pd.Series,
    prices: pd.Series | None = None,
    conventions: Conventions = DEFAULT_CONVENTIONS,
) -> DescriptiveStatistics:
    """Descriptive statistics of one daily return series.

    ``prices`` (the price path the returns were computed from, including the first
    price) enables cumulative and annualized returns; without it they are None.
    """
    r = returns.to_numpy(dtype="float64")
    if np.isnan(r).any():
        raise ValueError(f"{series_id}: returns contain missing values")
    if not np.isfinite(r).all():
        raise ValueError(f"{series_id}: returns contain non-finite values")
    n = len(r)
    notes: list[str] = []
    c = conventions

    mean = float(r.mean()) if n >= 1 else None
    median = float(np.median(r)) if n >= 1 else None
    rmin = float(r.min()) if n >= 1 else None
    rmax = float(r.max()) if n >= 1 else None
    # Detect constant series exactly: floating-point roundoff would otherwise give a tiny
    # non-zero deviation and meaningless higher moments.
    constant = n >= c.min_obs_std and bool((r == r[0]).all())
    if n < c.min_obs_std:
        std = None
        notes.append(f"standard deviation needs at least {c.min_obs_std} observations")
    else:
        std = 0.0 if constant else float(r.std(ddof=c.ddof))
    if constant:
        notes.append("constant returns: skewness and kurtosis are undefined")
    skew = float(stats.skew(r, bias=False)) if n >= c.min_obs_skew and not constant else None
    kurt = (
        float(stats.kurtosis(r, fisher=True, bias=False))
        if n >= c.min_obs_kurtosis and not constant
        else None
    )
    if n < c.min_obs_kurtosis and not constant:
        notes.append(
            f"skewness/kurtosis need at least {c.min_obs_skew}/{c.min_obs_kurtosis} observations"
        )

    cum = ann = None
    days: int | None = None
    if prices is not None:
        _check_price_path(series_id, returns, prices)
        cum = cumulative_return(prices)
        ann, days, reason = annualized_return(prices, c)
        if reason:
            notes.append(reason)
    else:
        notes.append("no price path supplied: cumulative and annualized returns unavailable")

    return DescriptiveStatistics(
        series_id=series_id,
        observations=n,
        start=returns.index[0].date().isoformat() if n else "",
        end=returns.index[-1].date().isoformat() if n else "",
        mean_daily=mean,
        median_daily=median,
        std_daily=std,
        min_daily=rmin,
        max_daily=rmax,
        skewness=skew,
        excess_kurtosis=kurt,
        cumulative_return=cum,
        annualized_return=ann,
        annualized_mean_return=mean * c.periods_per_year if mean is not None else None,
        annualized_volatility=annualized_volatility(std, c) if std is not None else None,
        elapsed_calendar_days=days,
        notes=tuple(notes),
    )


def _check_price_path(series_id: str, returns: pd.Series, prices: pd.Series) -> None:
    if len(prices) != len(returns) + 1 or not prices.index[1:].equals(returns.index):
        raise ValueError(f"{series_id}: price path does not match the return dates")


def histogram(returns: pd.Series, bins: int) -> tuple[np.ndarray, np.ndarray]:
    """Counts and bin edges of a return distribution (equal-width bins)."""
    if bins < 1:
        raise ValueError("bins must be positive")
    counts, edges = np.histogram(returns.to_numpy(dtype="float64"), bins=bins)
    return counts, edges
