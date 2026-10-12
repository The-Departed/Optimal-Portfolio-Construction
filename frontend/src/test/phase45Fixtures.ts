// SYNTHETIC API responses for UI tests only — not real estimates.
import type { CapmSummaryResponse } from "@/features/capm/types";
import type { SimulationResponse } from "@/features/portfolio/types";

const diag = {
  intercept_daily: 0.0002, intercept_std_error: 0.0001, intercept_t_stat: 2, intercept_p_value: 0.04,
  intercept_hac_p_value: 0.06, intercept_ci_low: 0.00001, intercept_ci_high: 0.0004, beta_std_error: 0.05,
  beta_t_stat: 24, beta_p_value: 0, beta_ci_low: 1.1, beta_ci_high: 1.3, beta_hac_std_error: 0.06,
  beta_hac_p_value: 0, hac_lags: 7, adj_r_squared: 0.39, residual_std_daily: 0.015,
  residual_volatility_annualized: 0.238, durbin_watson: 2.0,
};

export const capmSummary: CapmSummaryResponse = {
  status: "PASS_WITH_WARNINGS",
  sample_start: "2024-01-03",
  sample_end: "2024-12-31",
  observations: 240,
  periods_per_year: 252,
  market: { series_id: "IDX", mean_return: 0.12, annualized_volatility: 0.18, market_risk_premium: 0.07 },
  risk_free: { series_id: "RF", annualized_rate: 0.05, mean_quoted_yield: 0.049, convention: "as-of accrual.", first_auction_used: "2024-01-03", last_auction_used: "2024-12-25", max_staleness_days: 9 },
  definitions: { jensens_alpha: "historical - capm" },
  equities: [
    { asset_id: "AAA", name: "Alpha", sector: "Tech", status: "ok", error: null, observations: 240, start: "2024-01-03", end: "2024-12-31",
      historical_cagr: 0.15, historical_mean_return: 0.16, annualized_volatility: 0.3, beta: 1.2, capm_expected_return: 0.134,
      jensens_alpha: 0.026, intercept_annualized: 0.026, r_squared: 0.4, diagnostics: diag, warnings: [] },
    { asset_id: "BBB", name: "Beta", sector: "Bank", status: "failed", error: "240 observations; at least 300 required",
      observations: null, start: null, end: null, historical_cagr: null, historical_mean_return: null, annualized_volatility: null,
      beta: null, capm_expected_return: null, jensens_alpha: null, intercept_annualized: null, r_squared: null, diagnostics: null, warnings: [] },
  ],
  warnings: ["NIFTY 50 is a price index."],
  disclaimer: "Not a forecast.",
};

const dist = { min: 0.01, p05: 0.02, p25: 0.03, median: 0.04, p75: 0.05, p95: 0.06, max: 0.07, mean: 0.04, std: 0.01 };

export const simulation: SimulationResponse = {
  status: "PASS_WITH_WARNINGS",
  simulation_id: "mc_n50000_seed42",
  n_portfolios: 50000,
  seed: 42,
  method: "Dirichlet",
  inputs: {
    asset_order: ["AAA", "BBB"], expected_returns: { AAA: 0.1, BBB: 0.05 }, expected_return_convention: "arithmetic",
    covariance_convention: "sample", risk_free_rate: 0.05, risk_free_convention: "as-of", sample_start: "2024-01-03",
    sample_end: "2024-12-31", observations: 240, dataset_generated_at: "2026-01-01T00:00:00Z",
  },
  summary: { expected_return: dist, volatility: dist, sharpe_ratio: { ...dist, median: 0.83, max: 1.45 }, sharpe_undefined: 0 },
  candidates: [
    { label: "min_volatility", portfolio_id: 17, weights: [{ asset_id: "AAA", weight: 0.25 }, { asset_id: "BBB", weight: 0.75 }], expected_return: 0.0625, volatility: 0.047, sharpe_ratio: 0.27 },
    { label: "max_sharpe", portfolio_id: 99, weights: [{ asset_id: "AAA", weight: 0.6 }, { asset_id: "BBB", weight: 0.4 }], expected_return: 0.08, volatility: 0.085, sharpe_ratio: 1.454 },
  ],
  scatter: { portfolio_ids: [0, 1], expected_returns: [0.06, 0.07], volatilities: [0.05, 0.06], sharpe_ratios: [0.2, 0.33] },
  scatter_selection: "first draws",
  frontier: { portfolio_ids: [17, 99], expected_returns: [0.0625, 0.08], volatilities: [0.047, 0.085], sharpe_ratios: [0.27, 1.454] },
  frontier_label: "Monte Carlo approximation of the efficient frontier (not the exact frontier)",
  frontier_criterion: "non-dominated",
  checks: [{ name: "weights_valid", status: "pass", detail: "ok" }],
  warnings: ["Candidates are the best of a finite random sample, not guaranteed global optima."],
  output_files: { portfolios: "data/processed/simulations/mc_n50000_seed42.csv.gz" },
};
