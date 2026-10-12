"""CAPM analysis contracts (implemented in Phase 4)."""

from pydantic import Field

from app.schemas.common import ApiModel


class CapmRegressionDiagnostics(ApiModel):
    observations: int = Field(gt=0)
    alpha_t_stat: float
    alpha_p_value: float
    beta_t_stat: float
    beta_p_value: float
    beta_std_error: float
    durbin_watson: float


class CapmEquityResult(ApiModel):
    """CAPM evaluation of one equity; returns are annualized decimals."""

    asset_id: str
    annualized_return: float
    annualized_volatility: float = Field(ge=0)
    beta: float
    capm_expected_return: float
    jensens_alpha: float
    r_squared: float = Field(ge=0, le=1)
    diagnostics: CapmRegressionDiagnostics


class CapmSummaryResponse(ApiModel):
    risk_free_rate: float
    market_return: float
    equities: list[CapmEquityResult]
