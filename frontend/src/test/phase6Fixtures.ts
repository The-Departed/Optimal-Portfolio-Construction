// SYNTHETIC API responses for UI tests only — not real optimization results.
import type { FrontierResponse, InvestorProfile, OptimizationResponse } from "@/features/portfolio/types";
import { simulation } from "@/test/phase45Fixtures";

export function optimization(profile: InvestorProfile, overrides: Partial<OptimizationResponse> = {}): OptimizationResponse {
  const label = { conservative: "Conservative", balanced: "Balanced", growth: "Growth-oriented" }[profile];
  const ret = { conservative: 0.081, balanced: 0.1677, growth: 0.2307 }[profile];
  const vol = { conservative: 0.0355, balanced: 0.0754, growth: 0.12 }[profile];
  return {
    profile,
    label,
    objective: `${label} objective`,
    formulation: "minimize ...",
    status: "optimal",
    max_volatility: profile === "growth" ? 0.12 : null,
    portfolio: {
      weights: [{ asset_id: "AAA", weight: 0.3 }, { asset_id: "BBB", weight: 0.7 }],
      expected_return: ret,
      volatility: vol,
      sharpe_ratio: (ret - 0.05) / vol,
    },
    inputs: simulation.inputs,
    solver: {
      solver: "SLSQP", configuration: {}, success: true, convex_problem: true, best_start: "equal_weights",
      iterations: 12, starts_tried: 8, starts_accepted: 8,
      attempts: [], verification: {},
    },
    constraints: {
      sum_of_weights: 1, sum_residual_raw: 1e-15, bound_violation_raw: 0, min_weight: 0.3, max_weight: 0.7,
      volatility_limit: profile === "growth" ? 0.12 : null, volatility_slack: profile === "growth" ? -5e-14 : null,
      tolerance: { weights: 1e-8, volatility: 1e-8 }, feasible: true,
    },
    comparison: {
      simulation_id: "mc_n50000_seed42", n_portfolios: 50000, seed: 42,
      candidate: { label: profile, portfolio_id: 23123, weights: [{ asset_id: "AAA", weight: 0.4 }, { asset_id: "BBB", weight: 0.6 }],
        expected_return: ret - 0.0116, volatility: vol + 0.0096, sharpe_ratio: 1.4538 },
      candidate_rule: "highest-Sharpe simulated portfolio", candidate_satisfies_constraints: true,
      optimizer_passes_checks: true, return_difference: 0.0116, volatility_difference: -0.0096, sharpe_difference: 0.0309,
      note: "Same mu, Sigma, R_f.",
    },
    warnings: ["Weights are optimal for historical estimates."],
    ...overrides,
  };
}

export const frontier: FrontierResponse = {
  label: "Long-only efficient frontier",
  method: "SLSQP",
  asset_order: ["AAA", "BBB"],
  risk_free_rate: 0.05,
  points: [
    { expected_return: 0.08, volatility: 0.0355, sharpe_ratio: 0.85, weights: [0.1, 0.9] },
    { expected_return: 0.2, volatility: 0.1, sharpe_ratio: 1.5, weights: [0.7, 0.3] },
  ],
};
