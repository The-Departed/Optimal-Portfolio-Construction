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
  n_portfolios?: number;
  seed?: number;
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

export interface SimulationResponse {
  n_portfolios: number;
  seed: number;
  asset_order: string[];
  risk_free_rate: number;
  portfolios: SimulatedPortfolio[];
  frontier: PortfolioMetrics[];
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
