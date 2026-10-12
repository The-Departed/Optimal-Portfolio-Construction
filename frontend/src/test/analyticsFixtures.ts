// SYNTHETIC API responses for UI tests only — not real statistics.
import type { AnalyticsSummary, DistributionResponse, MatrixResponse, RiskFreeResponse, StatisticsResponse } from "@/features/analytics/types";

const stat = (series_id: string, role: "portfolio_asset" | "benchmark", ann: number | null) => ({
  series_id,
  name: series_id,
  role,
  observations: 100,
  start: "2024-01-03",
  end: "2024-05-31",
  mean_daily: 0.0005,
  median_daily: 0.0004,
  std_daily: 0.01,
  min_daily: -0.05,
  max_daily: 0.04,
  skewness: -0.25,
  excess_kurtosis: 3.5,
  cumulative_return: 0.05,
  annualized_return: ann,
  annualized_mean_return: 0.126,
  annualized_volatility: 0.1587,
  elapsed_calendar_days: 150,
  notes: ann === null ? ["interval of 150 calendar days is shorter than 365; not annualized"] : [],
});

export const analyticsSummary: AnalyticsSummary = {
  status: "PASS_WITH_WARNINGS",
  analytics_version: "3.0.0",
  computed_at: "2026-10-12T15:00:00Z",
  dataset_generated_at: "2026-10-12T12:00:00Z",
  dataset_status: "PASS_WITH_WARNINGS",
  sample: { start: "2024-01-03", end: "2024-05-31", price_start: "2024-01-02", observations: 100, multi_session_returns: 2 },
  assets: ["AAA", "BBB"],
  benchmark: "IDX",
  checks: [
    { name: "covariance_matrix", status: "pass", detail: "symmetric, PSD" },
    { name: "risk_free_conversion", status: "warn", detail: "daily conversion pending approval" },
  ],
  conventions: { periods_per_year: 252 },
  risk_free: null,
  upstream_warnings: [],
  disclaimer: "Historical, descriptive statistics only.",
};

export const statistics: StatisticsResponse = {
  sample: "common",
  periods_per_year: 252,
  calendar_days_per_year: 365.25,
  series: [stat("AAA", "portfolio_asset", 0.123), stat("BBB", "portfolio_asset", null), stat("IDX", "benchmark", 0.08)],
};

export const correlation: MatrixResponse = {
  kind: "correlation",
  frequency: null,
  labels: ["AAA", "BBB"],
  values: [
    [1, -0.3],
    [-0.3, 1],
  ],
  observations: 100,
  pairwise_observations: [
    [100, 100],
    [100, 100],
  ],
  start: "2024-01-03",
  end: "2024-05-31",
  diagnostics: { symmetric: true, positive_semidefinite: true, min_eigenvalue: 0.7, max_eigenvalue: 1.3, condition_number: 1.86, valid: true, problems: [] },
};

export const distribution: DistributionResponse = {
  series_id: "AAA",
  sample: "common",
  observations: 100,
  bin_edges: [-0.02, -0.01, 0, 0.01, 0.02],
  counts: [10, 40, 40, 10],
  mean_daily: 0.0005,
  std_daily: 0.01,
};

export const riskFree: RiskFreeResponse = {
  profile: {
    series_id: "RF",
    measure: "primary-auction implicit yield",
    units: "percent per annum",
    day_count: "actual/365",
    frequency: "weekly",
    observations: 2,
    first_date: "2024-01-03",
    last_date: "2024-01-10",
    lookback_observations: 0,
    median_gap_days: 7,
    max_gap_days: 7,
    min_yield_pct: 6.5,
    max_yield_pct: 6.6,
    mean_yield_pct: 6.55,
    conversion_status: "pending_approval",
    proposed_conversion: "as-of accrual (pending)",
    limitations: [],
  },
  error: null,
  observations: [
    { auction_date: "2024-01-03", implicit_yield_pct: 6.5, in_study_period: true },
    { auction_date: "2024-01-10", implicit_yield_pct: 6.6, in_study_period: true },
  ],
};
