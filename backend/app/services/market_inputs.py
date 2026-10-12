"""Shared inputs for CAPM (Phase 4) and Monte Carlo (Phase 5).

Built from the cached Phase 3 analytics result, so every analysis uses the same
validated common sample, conventions and risk-free treatment.
"""

import threading
from dataclasses import dataclass

import pandas as pd

from app.analytics.risk_free import RiskFreeAlignmentError, accrued_risk_free
from app.core.config import Settings
from app.core.errors import DataNotReadyError
from app.domain.assets import ASSET_IDS, BENCHMARK
from app.services.analytics_service import AnalyticsResult, AnalyticsService

RISK_FREE_CONVENTION = (
    "Per return interval (t-1, t]: latest 91-day T-bill auction yield with auction date "
    "<= t-1, accrued as y/100 x calendar_days/365 (simple interest, actual/365). "
    "Annualized R_f = periods_per_year x mean per-interval rf."
)
EXPECTED_RETURN_CONVENTION = (
    "Historical arithmetic mean of daily simple returns on the common sample x "
    "periods_per_year (methodology §3). Historical estimates, not forecasts."
)
MAX_STALENESS_DAYS = 35


@dataclass(frozen=True)
class MarketInputs:
    analytics: AnalyticsResult
    risk_free: pd.DataFrame  # per-interval rf, yield applied, auction used
    risk_free_annual: float
    expected_returns: pd.Series  # annualized arithmetic means, canonical order
    covariance: pd.DataFrame  # annualized, canonical order
    market_returns: pd.Series
    periods_per_year: int

    @property
    def mean_quoted_yield(self) -> float:
        return float(self.risk_free["yield_pct"].mean() / 100)

    @property
    def observed_intervals_per_year(self) -> float:
        idx = self.risk_free.index
        days = (idx[-1] - self.analytics.dataset.portfolio_prices.index[0]).days
        return len(idx) / (days / 365.25)


_cache: dict[tuple[str, str], MarketInputs] = {}
_lock = threading.Lock()


def build(result: AnalyticsResult) -> MarketInputs:
    prices = result.dataset.portfolio_prices
    try:
        rf = accrued_risk_free(
            prices.index[:-1],
            prices.index[1:],
            result.dataset.risk_free,
            max_staleness_days=MAX_STALENESS_DAYS,
        )
    except RiskFreeAlignmentError as exc:
        raise DataNotReadyError(
            f"Risk-free rate cannot be aligned with the return sample: {exc}",
            details={"stage": "risk_free"},
        ) from exc
    if not rf.index.equals(result.asset_returns.index):
        raise DataNotReadyError("Risk-free intervals do not match the return dates")
    ppy = result.conventions.periods_per_year
    stats = {s.series_id: s for s in result.statistics_common}
    mu = pd.Series({a: stats[a].annualized_mean_return for a in ASSET_IDS}, dtype="float64")
    return MarketInputs(
        analytics=result,
        risk_free=rf,
        risk_free_annual=float(rf["rf"].mean() * ppy),
        expected_returns=mu,
        covariance=result.covariance_annualized.loc[list(ASSET_IDS), list(ASSET_IDS)],
        market_returns=result.benchmark_returns[BENCHMARK.id],
        periods_per_year=ppy,
    )


def market_inputs(settings: Settings) -> MarketInputs:
    result = AnalyticsService(settings).result()
    key = (str(settings.data_dir), result.dataset.manifest_generated_at)
    with _lock:
        cached = _cache.get(key)
        if cached is None or cached.analytics is not result:
            cached = build(result)
            _cache[key] = cached
    return cached
