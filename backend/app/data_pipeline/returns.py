"""Daily simple returns for cleaned price, NAV and index series.

The formula lives in ``app.analytics.returns`` (single implementation for the whole
project); this module adds the pipeline-specific interval bookkeeping. Returns are not
annualized here and missing returns are never replaced with zero.
"""

import pandas as pd

from app.analytics.returns import simple_returns

__all__ = ["sessions_spanned", "simple_returns"]


def sessions_spanned(dates: pd.DatetimeIndex, calendar: pd.DatetimeIndex) -> pd.Series:
    """Number of reference sessions covered by each return interval (prev, t].

    1 means consecutive sessions; >1 means the return spans skipped sessions.
    The first date has no interval and is omitted.
    """
    pos = calendar.searchsorted(dates, side="right")
    spans = pos[1:] - pos[:-1]
    return pd.Series(spans, index=dates[1:], name="sessions_spanned")
