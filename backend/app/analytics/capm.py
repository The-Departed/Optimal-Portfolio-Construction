"""Single-index CAPM estimation for individual equities.

Regression (daily, per return interval t):

    R_i,t - R_f,t = a_i + b_i * (R_m,t - R_f,t) + e_i,t

estimated by OLS (statsmodels). Annualized quantities use the arithmetic convention
(daily mean x periods_per_year), consistent with the Phase 3 covariance annualization,
so Jensen's alpha equals periods_per_year x the daily intercept (an OLS identity, checked).
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

MIN_OBSERVATIONS = 60


class CapmEstimationError(ValueError):
    """The CAPM regression cannot be estimated reliably for this sample."""


@dataclass(frozen=True, slots=True)
class CapmRegression:
    observations: int
    start: str
    end: str
    intercept_daily: float
    intercept_std_error: float
    intercept_t_stat: float
    intercept_p_value: float
    intercept_ci_low: float
    intercept_ci_high: float
    beta: float
    beta_std_error: float
    beta_t_stat: float
    beta_p_value: float
    beta_ci_low: float
    beta_ci_high: float
    beta_hac_std_error: float
    beta_hac_p_value: float
    intercept_hac_p_value: float
    hac_lags: int
    r_squared: float
    adj_r_squared: float
    residual_std_daily: float
    durbin_watson: float


@dataclass(frozen=True, slots=True)
class CapmEvaluation:
    asset_id: str
    regression: CapmRegression
    historical_mean_return: float  # arithmetic, annualized
    capm_expected_return: float
    jensens_alpha: float
    intercept_annualized: float
    identity_gap: float  # |jensens_alpha - intercept_annualized|
    risk_free_annual: float
    market_mean_return: float


def build_sample(asset: pd.Series, market: pd.Series, risk_free: pd.Series) -> pd.DataFrame:
    """Align equity, market and risk-free returns on identical dates (inner join).

    Any missing value raises: observations are never dropped or zero-filled silently.
    """
    for name, s in (("asset", asset), ("market", market), ("risk_free", risk_free)):
        if s.isna().any():
            raise CapmEstimationError(
                f"{name} returns contain {int(s.isna().sum())} missing value(s)"
            )
    if not (asset.index.equals(market.index) and asset.index.equals(risk_free.index)):
        raise CapmEstimationError(
            "equity, market and risk-free series must cover identical dates; "
            f"lengths {len(asset)}, {len(market)}, {len(risk_free)}"
        )
    sample = pd.DataFrame({"asset": asset, "market": market, "rf": risk_free})
    sample["asset_excess"] = sample["asset"] - sample["rf"]
    sample["market_excess"] = sample["market"] - sample["rf"]
    return sample


def newey_west_lags(n: int) -> int:
    """Newey-West (1994) rule of thumb: floor(4 * (n / 100) ** (2 / 9))."""
    return math.floor(4 * (n / 100) ** (2 / 9))


def fit(sample: pd.DataFrame, *, min_observations: int = MIN_OBSERVATIONS) -> CapmRegression:
    n = len(sample)
    if n < min_observations:
        raise CapmEstimationError(f"{n} observations; at least {min_observations} required")
    x = sample["market_excess"].to_numpy(dtype="float64")
    y = sample["asset_excess"].to_numpy(dtype="float64")
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise CapmEstimationError("non-finite excess returns")
    if np.ptp(x) == 0:
        raise CapmEstimationError("market excess return is constant; beta is not identified")
    design = sm.add_constant(x, has_constant="add")
    lags = newey_west_lags(n)
    try:
        ols = sm.OLS(y, design).fit()
        hac = sm.OLS(y, design).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise CapmEstimationError(f"OLS failed: {exc}") from exc
    values = [*ols.params, *ols.bse, *ols.pvalues, *hac.bse, *hac.pvalues, ols.rsquared]
    if not np.isfinite(values).all():
        raise CapmEstimationError("OLS produced non-finite estimates")
    ci = ols.conf_int(alpha=0.05)
    return CapmRegression(
        observations=n,
        start=sample.index[0].date().isoformat(),
        end=sample.index[-1].date().isoformat(),
        intercept_daily=float(ols.params[0]),
        intercept_std_error=float(ols.bse[0]),
        intercept_t_stat=float(ols.tvalues[0]),
        intercept_p_value=float(ols.pvalues[0]),
        intercept_ci_low=float(ci[0][0]),
        intercept_ci_high=float(ci[0][1]),
        beta=float(ols.params[1]),
        beta_std_error=float(ols.bse[1]),
        beta_t_stat=float(ols.tvalues[1]),
        beta_p_value=float(ols.pvalues[1]),
        beta_ci_low=float(ci[1][0]),
        beta_ci_high=float(ci[1][1]),
        beta_hac_std_error=float(hac.bse[1]),
        beta_hac_p_value=float(hac.pvalues[1]),
        intercept_hac_p_value=float(hac.pvalues[0]),
        hac_lags=lags,
        r_squared=float(ols.rsquared),
        adj_r_squared=float(ols.rsquared_adj),
        residual_std_daily=float(math.sqrt(ols.mse_resid)),
        durbin_watson=float(durbin_watson(ols.resid)),
    )


def capm_expected_return(beta: float, risk_free_annual: float, market_annual: float) -> float:
    """E(R_i) = R_f + beta * (E(R_m) - R_f), all annualized decimals."""
    return risk_free_annual + beta * (market_annual - risk_free_annual)


def evaluate(
    asset_id: str,
    sample: pd.DataFrame,
    *,
    periods_per_year: int,
    min_observations: int = MIN_OBSERVATIONS,
) -> CapmEvaluation:
    reg = fit(sample, min_observations=min_observations)
    rf_annual = float(sample["rf"].mean() * periods_per_year)
    market_annual = float(sample["market"].mean() * periods_per_year)
    historical = float(sample["asset"].mean() * periods_per_year)
    expected = capm_expected_return(reg.beta, rf_annual, market_annual)
    alpha = historical - expected
    intercept_annual = reg.intercept_daily * periods_per_year
    return CapmEvaluation(
        asset_id=asset_id,
        regression=reg,
        historical_mean_return=historical,
        capm_expected_return=expected,
        jensens_alpha=alpha,
        intercept_annualized=intercept_annual,
        identity_gap=abs(alpha - intercept_annual),
        risk_free_annual=rf_annual,
        market_mean_return=market_annual,
    )
