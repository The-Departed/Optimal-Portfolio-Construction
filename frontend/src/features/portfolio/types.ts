// Mirrors backend/app/schemas/portfolio.py. Weights follow the canonical asset order.
import type { PortfolioMetrics } from "@/types/api";

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
}

export interface AssetWeight {
  asset_id: string;
  weight: number;
}

export interface SimulatedPortfolio extends PortfolioMetrics {
  weights: number[];
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

export interface OptimizationResponse {
  profile: InvestorProfile;
  max_volatility: number | null;
  weights: AssetWeight[];
  metrics: PortfolioMetrics;
  risk_free_rate: number;
  solver_message: string;
  best_simulated: SimulatedPortfolio | null;
}
