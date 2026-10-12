"""Portfolio simulation and optimization contracts (implemented in Phases 5-6)."""

from typing import Self

from pydantic import Field, model_validator

from app.domain.profiles import InvestorProfile
from app.schemas.common import ApiModel, PortfolioMetrics


class ProfileDefinitionOut(ApiModel):
    profile: InvestorProfile
    label: str
    objective: str
    formulation: str
    requires_max_volatility: bool


class SimulationRequest(ApiModel):
    n_portfolios: int = Field(default=50_000, ge=100, le=200_000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, description="numpy default_rng seed")
    scatter_points: int = Field(
        default=2_000, ge=100, le=10_000, description="Portfolios returned for plotting"
    )


class OptimizationRequest(ApiModel):
    profile: InvestorProfile
    max_volatility: float | None = Field(
        default=None,
        gt=0,
        lt=5,
        description="Annualized sigma_max as a decimal (0.15 == 15%). Required for growth.",
    )

    @model_validator(mode="after")
    def _check_max_volatility(self) -> Self:
        if self.profile is InvestorProfile.GROWTH and self.max_volatility is None:
            raise ValueError("max_volatility is required for the growth profile")
        if self.profile is not InvestorProfile.GROWTH and self.max_volatility is not None:
            raise ValueError("max_volatility applies only to the growth profile")
        return self


class AssetWeight(ApiModel):
    asset_id: str
    weight: float = Field(ge=0, le=1)


class SimulatedPortfolio(PortfolioMetrics):
    weights: list[float] = Field(description="Weights in canonical asset order.")


class CandidatePortfolio(ApiModel):
    label: str = Field(description="min_volatility or max_sharpe (simulation candidates)")
    portfolio_id: int
    weights: list[AssetWeight]
    expected_return: float
    volatility: float
    sharpe_ratio: float | None


class Distribution(ApiModel):
    min: float
    p05: float
    p25: float
    median: float
    p75: float
    p95: float
    max: float
    mean: float
    std: float


class SimulationSummary(ApiModel):
    expected_return: Distribution
    volatility: Distribution
    sharpe_ratio: Distribution
    sharpe_undefined: int = Field(description="Portfolios with volatility below the floor")


class PointSet(ApiModel):
    """Columnar portfolio metrics for plotting."""

    portfolio_ids: list[int]
    expected_returns: list[float]
    volatilities: list[float]
    sharpe_ratios: list[float | None]


class SimulationInputs(ApiModel):
    asset_order: list[str]
    expected_returns: dict[str, float]
    expected_return_convention: str
    covariance_convention: str
    risk_free_rate: float
    risk_free_convention: str
    sample_start: str
    sample_end: str
    observations: int
    dataset_generated_at: str


class SimulationCheck(ApiModel):
    name: str
    status: str
    detail: str


class SimulationResponse(ApiModel):
    status: str = Field(description="PASS, PASS_WITH_WARNINGS or FAILED")
    simulation_id: str
    n_portfolios: int
    seed: int
    method: str
    inputs: SimulationInputs
    summary: SimulationSummary
    candidates: list[CandidatePortfolio]
    scatter: PointSet
    scatter_selection: str
    frontier: PointSet
    frontier_label: str
    frontier_criterion: str
    checks: list[SimulationCheck]
    warnings: list[str]
    output_files: dict[str, str]


class OptimizationResponse(ApiModel):
    profile: InvestorProfile
    max_volatility: float | None
    weights: list[AssetWeight]
    metrics: PortfolioMetrics
    risk_free_rate: float
    solver_message: str
    best_simulated: SimulatedPortfolio | None = None
