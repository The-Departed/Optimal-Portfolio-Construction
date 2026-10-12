"""Portfolio simulation (Phase 5) and optimization (Phase 6) contracts."""

from typing import Self

from pydantic import Field, model_validator

from app.domain.profiles import InvestorProfile
from app.schemas.common import ApiModel


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
    simulation_portfolios: int = Field(
        default=50_000, ge=100, le=200_000, description="Monte Carlo run used for comparison"
    )
    simulation_seed: int = Field(default=42, ge=0, le=2**32 - 1)

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


class OptimizedPortfolio(ApiModel):
    weights: list[AssetWeight]
    expected_return: float
    volatility: float
    sharpe_ratio: float | None


class SolverAttempt(ApiModel):
    label: str
    success: bool
    accepted: bool
    message: str
    iterations: int
    evaluations: int


class SolverDiagnostics(ApiModel):
    solver: str
    configuration: dict[str, object]
    success: bool
    convex_problem: bool
    best_start: str
    iterations: int
    starts_tried: int
    starts_accepted: int
    attempts: list[SolverAttempt]
    verification: dict[str, float]


class ConstraintCheck(ApiModel):
    sum_of_weights: float
    sum_residual_raw: float = Field(description="|sum(w) - 1| of the raw solver output")
    bound_violation_raw: float = Field(description="Max violation of 0 <= w <= 1 before cleanup")
    min_weight: float
    max_weight: float
    volatility_limit: float | None
    volatility_slack: float | None = Field(description="sigma_max - volatility (growth only)")
    tolerance: dict[str, float]
    feasible: bool


class SimulationComparison(ApiModel):
    simulation_id: str
    n_portfolios: int
    seed: int
    candidate: CandidatePortfolio | None
    candidate_rule: str
    candidate_satisfies_constraints: bool | None
    optimizer_passes_checks: bool
    return_difference: float | None = Field(description="optimizer - candidate")
    volatility_difference: float | None
    sharpe_difference: float | None
    note: str


class EstimationInputs(ApiModel):
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


class OptimizationResponse(ApiModel):
    profile: InvestorProfile
    label: str
    objective: str
    formulation: str
    status: str = Field(description="optimal: solver converged and every constraint check passed")
    max_volatility: float | None
    portfolio: OptimizedPortfolio
    inputs: EstimationInputs
    solver: SolverDiagnostics
    constraints: ConstraintCheck
    comparison: SimulationComparison
    warnings: list[str]


class FrontierPoint(ApiModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float | None
    weights: list[float] = Field(description="Canonical asset order")


class FrontierResponse(ApiModel):
    label: str
    method: str
    asset_order: list[str]
    risk_free_rate: float
    points: list[FrontierPoint]
