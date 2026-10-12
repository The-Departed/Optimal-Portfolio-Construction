"""Reference calendar and common-date alignment.

The reference NSE trading calendar is the union of trading dates observed in the six
equity series (liquid large caps that trade in every session). NSE's official holiday
calendar is not available to automated clients, so this observed calendar is used;
it includes special sessions such as Muhurat trading.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from app.data_pipeline.returns import sessions_spanned, simple_returns


def reference_calendar(
    series: Mapping[str, pd.Series], start: pd.Timestamp, end: pd.Timestamp
) -> pd.DatetimeIndex:
    dates: set[pd.Timestamp] = set()
    for s in series.values():
        dates.update(s.index)
    cal = pd.DatetimeIndex(sorted(dates))
    return cal[(cal >= start) & (cal <= end)]


@dataclass(frozen=True)
class AlignedData:
    portfolio_prices: pd.DataFrame
    benchmark_prices: pd.DataFrame
    portfolio_returns: pd.DataFrame
    benchmark_returns: pd.DataFrame
    sessions_spanned: pd.Series
    excluded_sessions: dict[str, list[pd.Timestamp]]

    @property
    def common_dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.portfolio_prices.index)

    @property
    def multi_session_returns(self) -> pd.Series:
        return self.sessions_spanned[self.sessions_spanned > 1]


def align(
    portfolio: Mapping[str, pd.Series],
    benchmark: tuple[str, pd.Series],
    calendar: pd.DatetimeIndex,
) -> AlignedData:
    """Inner-join all series on dates present in every series and the calendar.

    No values are filled: a date missing from any series is dropped for all, and the
    next return spans the gap (reported via ``sessions_spanned``).
    """
    bench_id, bench = benchmark
    all_series = {**portfolio, bench_id: bench}
    common = calendar
    for s in all_series.values():
        common = common.intersection(pd.DatetimeIndex(s.index))
    common = common.sort_values()
    if len(common) < 2:
        raise ValueError("Fewer than two common dates; alignment impossible")

    excluded = {
        name: sorted(set(calendar) - set(pd.DatetimeIndex(s.index)))
        for name, s in all_series.items()
    }
    portfolio_prices = pd.DataFrame({k: v.reindex(common) for k, v in portfolio.items()})
    benchmark_prices = pd.DataFrame({bench_id: bench.reindex(common)})
    for frame in (portfolio_prices, benchmark_prices):
        frame.index.name = "date"
    return AlignedData(
        portfolio_prices=portfolio_prices,
        benchmark_prices=benchmark_prices,
        portfolio_returns=simple_returns(portfolio_prices),
        benchmark_returns=simple_returns(benchmark_prices),
        sessions_spanned=sessions_spanned(common, calendar),
        excluded_sessions=excluded,
    )
