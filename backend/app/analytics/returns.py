"""Daily simple returns for price-like series (prices, NAVs, index levels).

r_t = P_t / P_(t-1) - 1. Inputs must already be validated: missing or non-positive
prices raise instead of becoming zero or NaN returns. Yields are not prices and are
rejected (see ``returns_for``).
"""

from typing import overload

import numpy as np
import pandas as pd

PRICE_LIKE_KINDS = frozenset({"price", "nav", "index_level"})


class NotAPriceSeriesError(TypeError):
    """Raised when a return calculation is attempted on a non-price series (e.g. yields)."""


def _check_prices(prices: pd.Series | pd.DataFrame) -> None:
    index = prices.index
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("prices must be indexed by dates")
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError("price dates must be strictly increasing")
    values = prices.to_numpy(dtype="float64")
    if np.isnan(values).any():
        raise ValueError("prices contain missing values; align or clean them first")
    if not np.isfinite(values).all():
        raise ValueError("prices contain non-finite values")
    if (values <= 0).any():
        raise ValueError("prices must be strictly positive")


@overload
def simple_returns(prices: pd.Series, *, keep_first: bool = False) -> pd.Series: ...
@overload
def simple_returns(prices: pd.DataFrame, *, keep_first: bool = False) -> pd.DataFrame: ...


def simple_returns(
    prices: pd.Series | pd.DataFrame, *, keep_first: bool = False
) -> pd.Series | pd.DataFrame:
    """Simple returns of validated prices.

    The first observation has no prior price, so its return is undefined: it is
    dropped, or kept as NaN when ``keep_first`` is true. No other NaN can occur.
    """
    _check_prices(prices)
    returns = prices / prices.shift(1) - 1.0
    return returns if keep_first else returns.iloc[1:]


def returns_for(prices: pd.Series, value_kind: str) -> pd.Series:
    """Simple returns, guarded by the series' recorded value kind."""
    if value_kind not in PRICE_LIKE_KINDS:
        raise NotAPriceSeriesError(
            f"Cannot compute price returns for a {value_kind!r} series; "
            "yields must be converted with an approved rate convention instead"
        )
    return simple_returns(prices)


def max_return_discrepancy(returns: pd.DataFrame, prices: pd.DataFrame) -> float:
    """Largest absolute difference between ``returns`` and returns recomputed from ``prices``.

    Raises if dates or columns differ, so a misaligned return table cannot pass.
    """
    recomputed = simple_returns(prices)
    if not returns.index.equals(recomputed.index):
        raise ValueError("return dates do not match the price dates (excluding the first)")
    if list(returns.columns) != list(recomputed.columns):
        raise ValueError("return columns do not match the price columns")
    return float(np.abs(returns.to_numpy() - recomputed.to_numpy()).max())
