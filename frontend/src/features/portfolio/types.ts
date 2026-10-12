// Mirrors backend/app/schemas/portfolio.py. Weights follow the canonical asset order.

export type InvestorProfile = "conservative" | "balanced" | "growth";

export interface ProfileDefinition {
  profile: InvestorProfile;
  label: string;
  objective: string;
  formulation: string;
  requires_max_volatility: boolean;
}

export interface SimulationRequest {
  n_portfolios: number;
  seed: number;
  scatter_points?: number;
}

export interface OptimizationRequest {
  profile: InvestorProfile;
  /** Annualized sigma_max as a decimal (0.15 == 15%). Growth profile only. */
  max_volatility?: number;
  simulation_portfolios?: number;
  simulation_seed?: number;
}

export interface AssetWeight {
  asset_id: string;
  weight: number;
}

export interface CandidatePortfolio {
  label: "min_volatility" | "max_sharpe";
  portfolio_id: number;
  weights: AssetWeight[];
  expected_return: number;
  volatility: number;
  sharpe_ratio: number | null;
}

export interface Distribution {
  min: number;
  p05: number;
  p25: number;
  median: number;
  p75: number;
  p95: number;
  max: number;
  mean: number;
  std: number;
}

export interface PointSet {
  portfolio_ids: number[];
  expected_returns: number[];
  volatilities: number[];
  sharpe_ratios: (number | null)[];
}

export interface SimulationResponse {
  status: "PASS" | "PASS_WITH_WARNINGS" | "FAILED";
  simulation_id: string;
  n_portfolios: number;
  seed: number;
  method: string;
  inputs: {
    asset_order: string[];
    expected_returns: Record<string, number>;
    expected_return_convention: string;
    covariance_convention: string;
    risk_free_rate: number;
    risk_free_convention: string;
    sample_start: string;
    sample_end: string;
    observations: number;
    dataset_generated_at: string;
  };
  summary: { expected_return: Distribution; volatility: Distribution; sharpe_ratio: Distribution; sharpe_undefined: number };
  candidates: CandidatePortfolio[];
  scatter: PointSet;
  scatter_selection: string;
  frontier: PointSet;
  frontier_label: string;
  frontier_criterion: string;
  checks: { name: string; status: "pass" | "warn" | "fail"; detail: string }[];
  warnings: string[];
  output_files: Record<string, string>;
}

export interface SolverAttempt {
  label: string;
  success: boolean;
  accepted: boolean;
  message: string;
  iterations: number;
  evaluations: number;
}

export interface OptimizationResponse {
  profile: InvestorProfile;
  label: string;
  objective: string;
  formulation: string;
  status: "optimal";
  max_volatility: number | null;
  portfolio: { weights: AssetWeight[]; expected_return: number; volatility: number; sharpe_ratio: number | null };
  inputs: SimulationResponse["inputs"];
  solver: {
    solver: string;
    configuration: Record<string, unknown>;
    success: boolean;
    convex_problem: boolean;
    best_start: string;
    iterations: number;
    starts_tried: number;
    starts_accepted: number;
    attempts: SolverAttempt[];
    verification: Record<string, number>;
  };
  constraints: {
    sum_of_weights: number;
    sum_residual_raw: number;
    bound_violation_raw: number;
    min_weight: number;
    max_weight: number;
    volatility_limit: number | null;
    volatility_slack: number | null;
    tolerance: Record<string, number>;
    feasible: boolean;
  };
  comparison: {
    simulation_id: string;
    n_portfolios: number;
    seed: number;
    candidate: Omit<CandidatePortfolio, "label"> & { label: string } | null;
    candidate_rule: string;
    candidate_satisfies_constraints: boolean | null;
    optimizer_passes_checks: boolean;
    return_difference: number | null;
    volatility_difference: number | null;
    sharpe_difference: number | null;
    note: string;
  };
  warnings: string[];
}

export interface FrontierResponse {
  label: string;
  method: string;
  asset_order: string[];
  risk_free_rate: number;
  points: { expected_return: number; volatility: number; sharpe_ratio: number | null; weights: number[] }[];
}
