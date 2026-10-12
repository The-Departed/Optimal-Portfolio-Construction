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
    n_portfolios: int = Field(default=50_000, gt=0, le=200_000)
    seed: int | None = Field(default=None, ge=0, description="Defaults to the configured seed.")


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


class SimulationResponse(ApiModel):
    n_portfolios: int
    seed: int
    asset_order: list[str]
    risk_free_rate: float
    portfolios: list[SimulatedPortfolio]
    frontier: list[PortfolioMetrics]


class OptimizationResponse(ApiModel):
    profile: InvestorProfile
    max_volatility: float | None
    weights: list[AssetWeight]
    metrics: PortfolioMetrics
    risk_free_rate: float
    solver_message: str
    best_simulated: SimulatedPortfolio | None = None
