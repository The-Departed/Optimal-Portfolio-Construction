// Mirrors backend/app/schemas/analytics.py. Returns are decimals (0.12 == 12%).

export type Sample = "common" | "individual";
export type CheckStatus = "pass" | "warn" | "fail";

export interface AnalyticsCheck {
  name: string;
  status: CheckStatus;
  detail: string;
}

export interface RiskFreeProfile {
  series_id: string;
  measure: string;
  units: string;
  day_count: string;
  frequency: string;
  observations: number;
  first_date: string;
  last_date: string;
  lookback_observations: number;
  median_gap_days: number;
  max_gap_days: number;
  min_yield_pct: number;
  max_yield_pct: number;
  mean_yield_pct: number;
  conversion_status: string;
  proposed_conversion: string;
  limitations: string[];
}

export interface AnalyticsSummary {
  status: "PASS" | "PASS_WITH_WARNINGS" | "FAILED";
  analytics_version: string;
  computed_at: string;
  dataset_generated_at: string;
  dataset_status: string;
  sample: { start: string; end: string; price_start: string; observations: number; multi_session_returns: number };
  assets: string[];
  benchmark: string;
  checks: AnalyticsCheck[];
  conventions: Record<string, unknown>;
  risk_free: RiskFreeProfile | null;
  upstream_warnings: string[];
  disclaimer: string;
}

export interface SeriesStatistics {
  series_id: string;
  name: string;
  role: "portfolio_asset" | "benchmark";
  observations: number;
  start: string;
  end: string;
  mean_daily: number | null;
  median_daily: number | null;
  std_daily: number | null;
  min_daily: number | null;
  max_daily: number | null;
  skewness: number | null;
  excess_kurtosis: number | null;
  cumulative_return: number | null;
  annualized_return: number | null;
  annualized_mean_return: number | null;
  annualized_volatility: number | null;
  elapsed_calendar_days: number | null;
  notes: string[];
}

export interface StatisticsResponse {
  sample: Sample;
  periods_per_year: number;
  calendar_days_per_year: number;
  series: SeriesStatistics[];
}

export interface MatrixResponse {
  kind: "correlation" | "covariance";
  frequency: "daily" | "annualized" | null;
  labels: string[];
  values: number[][];
  observations: number;
  pairwise_observations: number[][];
  start: string;
  end: string;
  diagnostics: {
    symmetric: boolean;
    positive_semidefinite: boolean;
    min_eigenvalue: number;
    max_eigenvalue: number;
    condition_number: number | null;
    valid: boolean;
    problems: string[];
  };
}

export interface DistributionResponse {
  series_id: string;
  sample: Sample;
  observations: number;
  bin_edges: number[];
  counts: number[];
  mean_daily: number | null;
  std_daily: number | null;
}

export interface RiskFreeResponse {
  profile: RiskFreeProfile | null;
  error: string | null;
  observations: { auction_date: string; implicit_yield_pct: number; in_study_period: boolean }[];
}
