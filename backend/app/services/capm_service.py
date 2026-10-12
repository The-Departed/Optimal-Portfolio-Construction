"""CAPM equity evaluation (Phase 4): orchestration and serialization."""

import math

from app.analytics.capm import CapmEstimationError, build_sample, evaluate
from app.core.config import Settings
from app.core.errors import InvalidParameterError
from app.domain.assets import BENCHMARK, EQUITY_IDS, get_asset
from app.schemas.capm import (
    CapmDiagnostics,
    CapmEquityResult,
    CapmMarket,
    CapmRiskFree,
    CapmSummaryResponse,
)
from app.services.market_inputs import RISK_FREE_CONVENTION, MarketInputs, market_inputs

IDENTITY_TOLERANCE = 1e-10

DEFINITIONS = {
    "regression": "R_i,t - R_f,t = a_i + b_i (R_m,t - R_f,t) + e_i,t, OLS on daily (per-interval) "
    "excess returns of the common sample; R_m = NIFTY 50 price-index return",
    "intercept_daily": "a_i, decimal return per trading interval (not annualized)",
    "intercept_annualized": "a_i x periods_per_year",
    "historical_mean_return": "periods_per_year x mean daily simple return (arithmetic)",
    "historical_cagr": "(P_end / P_start)^(365.25 / days) - 1; descriptive only, not used in alpha",
    "capm_expected_return": "E(R_i) = R_f + beta_i (E(R_m) - R_f), all arithmetic annualized",
    "jensens_alpha": "historical_mean_return - capm_expected_return (annualized). With these "
    "conventions it equals intercept_annualized exactly (OLS identity); the identity is checked",
    "significance": "OLS standard errors, t-stats, p-values and 95% CIs; Newey-West HAC p-values "
    "as a robustness check",
}


def _equity_result(asset_id: str, inputs: MarketInputs) -> CapmEquityResult:
    asset = get_asset(asset_id)
    base = {"asset_id": asset_id, "name": asset.name, "sector": asset.sector}
    stats = next(s for s in inputs.analytics.statistics_common if s.series_id == asset_id)
    try:
        sample = build_sample(
            inputs.analytics.asset_returns[asset_id], inputs.market_returns, inputs.risk_free["rf"]
        )
        ev = evaluate(asset_id, sample, periods_per_year=inputs.periods_per_year)
    except CapmEstimationError as exc:
        return CapmEquityResult(**base, status="failed", error=str(exc))
    if ev.identity_gap > IDENTITY_TOLERANCE:
        return CapmEquityResult(
            **base,
            status="failed",
            error=f"Jensen's alpha and annualized intercept disagree by {ev.identity_gap:.2e}",
        )
    reg = ev.regression
    warnings = []
    if reg.intercept_p_value >= 0.05:
        warnings.append(
            f"Intercept not statistically different from zero (p = {reg.intercept_p_value:.2f})"
        )
    return CapmEquityResult(
        **base,
        status="ok",
        observations=reg.observations,
        start=reg.start,
        end=reg.end,
        historical_cagr=stats.annualized_return,
        historical_mean_return=ev.historical_mean_return,
        annualized_volatility=stats.annualized_volatility,
        beta=reg.beta,
        capm_expected_return=ev.capm_expected_return,
        jensens_alpha=ev.jensens_alpha,
        intercept_annualized=ev.intercept_annualized,
        r_squared=reg.r_squared,
        diagnostics=CapmDiagnostics(
            intercept_daily=reg.intercept_daily,
            intercept_std_error=reg.intercept_std_error,
            intercept_t_stat=reg.intercept_t_stat,
            intercept_p_value=reg.intercept_p_value,
            intercept_hac_p_value=reg.intercept_hac_p_value,
            intercept_ci_low=reg.intercept_ci_low,
            intercept_ci_high=reg.intercept_ci_high,
            beta_std_error=reg.beta_std_error,
            beta_t_stat=reg.beta_t_stat,
            beta_p_value=reg.beta_p_value,
            beta_ci_low=reg.beta_ci_low,
            beta_ci_high=reg.beta_ci_high,
            beta_hac_std_error=reg.beta_hac_std_error,
            beta_hac_p_value=reg.beta_hac_p_value,
            hac_lags=reg.hac_lags,
            adj_r_squared=reg.adj_r_squared,
            residual_std_daily=reg.residual_std_daily,
            residual_volatility_annualized=reg.residual_std_daily
            * math.sqrt(inputs.periods_per_year),
            durbin_watson=reg.durbin_watson,
        ),
        warnings=warnings,
    )


def resolve_equities(requested: list[str] | None) -> list[str]:
    if not requested:
        return list(EQUITY_IDS)
    ids = [s.strip().upper() for item in requested for s in item.split(",") if s.strip()]
    unknown = [s for s in ids if s not in EQUITY_IDS]
    if unknown:
        raise InvalidParameterError(
            f"CAPM applies to the six equities only; unknown or non-equity {unknown}",
            details={"valid": list(EQUITY_IDS)},
        )
    return [e for e in EQUITY_IDS if e in ids]


def summary_warnings(inputs: MarketInputs) -> list[str]:
    a = inputs.analytics
    multi = len(a.multi_session_dates)
    return [
        "NIFTY 50 is a price index (dividends excluded) while equity returns include "
        "dividends; E(R_m) is understated, which overstates Jensen's alpha by roughly "
        "beta x the index dividend yield.",
        f"Risk-free proxy: weekly 91-day T-bill auction yields carried forward between "
        f"auctions (up to {int(inputs.risk_free['staleness_days'].max())} days) and accrued "
        "daily; a term yield used as a short-rate proxy. Conversion convention awaits "
        "formal approval.",
        f"Annualization uses {inputs.periods_per_year} periods per year, while the common sample "
        f"has about {inputs.observed_intervals_per_year:.1f} return intervals per year; the "
        f"annualized risk-free rate ({inputs.risk_free_annual:.2%}) therefore exceeds the "
        f"average quoted yield ({inputs.mean_quoted_yield:.2%}). Returns and the risk-free "
        "rate are scaled identically, so excess returns remain consistent.",
        f"{multi} return intervals span more than one session; their risk-free accrual covers "
        "the full calendar interval.",
        "Historical alpha is not evidence that a stock is mispriced and is not a forecast.",
    ]


class CapmService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summary(self, equities: list[str] | None = None) -> CapmSummaryResponse:
        ids = resolve_equities(equities)
        inputs = market_inputs(self._settings)
        results = [_equity_result(e, inputs) for e in ids]
        stats = {s.series_id: s for s in inputs.analytics.statistics_common}
        market_mean = float(inputs.market_returns.mean() * inputs.periods_per_year)
        rf = inputs.risk_free
        failed = [r for r in results if r.status != "ok"]
        return CapmSummaryResponse(
            status="FAILED" if failed else "PASS_WITH_WARNINGS",
            sample_start=inputs.analytics.sample_start,
            sample_end=inputs.analytics.sample_end,
            observations=len(inputs.analytics.asset_returns),
            periods_per_year=inputs.periods_per_year,
            market=CapmMarket(
                series_id=BENCHMARK.id,
                mean_return=market_mean,
                annualized_volatility=stats[BENCHMARK.id].annualized_volatility or 0.0,
                market_risk_premium=market_mean - inputs.risk_free_annual,
            ),
            risk_free=CapmRiskFree(
                series_id="RF_TBILL_91D",
                annualized_rate=inputs.risk_free_annual,
                mean_quoted_yield=inputs.mean_quoted_yield,
                convention=RISK_FREE_CONVENTION,
                first_auction_used=str(rf["auction_date"].min().date()),
                last_auction_used=str(rf["auction_date"].max().date()),
                max_staleness_days=int(rf["staleness_days"].max()),
            ),
            definitions=DEFINITIONS,
            equities=results,
            warnings=summary_warnings(inputs),
            disclaimer="CAPM estimates describe the historical sample. A positive or negative "
            "alpha does not establish that a stock is under- or overpriced and does not "
            "forecast future returns.",
        )
