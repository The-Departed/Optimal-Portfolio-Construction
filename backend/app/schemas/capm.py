"""CAPM equity-evaluation contracts (Phase 4).

Returns are decimals (0.12 == 12%). Fields ending in ``_daily`` are per return
interval; annualized fields use the arithmetic x periods_per_year convention unless
named ``historical_cagr``.
"""

from pydantic import Field

from app.schemas.common import ApiModel


class CapmDiagnostics(ApiModel):
    intercept_daily: float = Field(
        description="Regression intercept a_i, decimal per trading interval"
    )
    intercept_std_error: float
    intercept_t_stat: float
    intercept_p_value: float
    intercept_hac_p_value: float
    intercept_ci_low: float = Field(description="95% CI, daily units")
    intercept_ci_high: float
    beta_std_error: float
    beta_t_stat: float
    beta_p_value: float
    beta_ci_low: float = Field(description="95% CI")
    beta_ci_high: float
    beta_hac_std_error: float = Field(description="Newey-West HAC standard error")
    beta_hac_p_value: float
    hac_lags: int
    adj_r_squared: float
    residual_std_daily: float
    residual_volatility_annualized: float = Field(description="Idiosyncratic volatility")
    durbin_watson: float


class CapmEquityResult(ApiModel):
    asset_id: str
    name: str
    sector: str
    status: str = Field(description="ok, or failed with an error")
    error: str | None = None
    observations: int | None = None
    start: str | None = None
    end: str | None = None
    historical_cagr: float | None = Field(default=None, description="Descriptive (Phase 3 CAGR)")
    historical_mean_return: float | None = Field(
        default=None, description="Arithmetic annualized mean return (used for Jensen's alpha)"
    )
    annualized_volatility: float | None = None
    beta: float | None = None
    capm_expected_return: float | None = None
    jensens_alpha: float | None = Field(
        default=None, description="historical_mean_return - capm_expected_return (annualized)"
    )
    intercept_annualized: float | None = Field(
        default=None, description="Regression intercept x periods_per_year"
    )
    r_squared: float | None = None
    diagnostics: CapmDiagnostics | None = None
    warnings: list[str] = Field(default_factory=list)


class CapmMarket(ApiModel):
    series_id: str
    mean_return: float = Field(description="E(R_m): arithmetic annualized mean of NIFTY 50 returns")
    annualized_volatility: float
    market_risk_premium: float = Field(description="E(R_m) - R_f")


class CapmRiskFree(ApiModel):
    series_id: str
    annualized_rate: float = Field(description="periods_per_year x mean per-interval rf")
    mean_quoted_yield: float = Field(description="Average of the yields applied, decimal p.a.")
    convention: str
    first_auction_used: str
    last_auction_used: str
    max_staleness_days: int


class CapmSummaryResponse(ApiModel):
    status: str = Field(description="PASS, PASS_WITH_WARNINGS or FAILED")
    sample_start: str
    sample_end: str
    observations: int
    periods_per_year: int
    market: CapmMarket
    risk_free: CapmRiskFree
    definitions: dict[str, str]
    equities: list[CapmEquityResult]
    warnings: list[str]
    disclaimer: str
