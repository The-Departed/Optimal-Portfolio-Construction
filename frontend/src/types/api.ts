// Mirrors backend/app/schemas/common.py and data_status.py. Keep in sync with the API.

export type ErrorCode =
  | "VALIDATION_ERROR"
  | "DATA_NOT_READY"
  | "NOT_IMPLEMENTED"
  | "OPTIMIZATION_FAILED"
  | "INFEASIBLE_CONSTRAINT"
  | "INTERNAL_ERROR";

export interface ErrorResponse {
  code: ErrorCode;
  message: string;
  details: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export type DatasetState = "missing" | "invalid" | "validation_failed" | "ready";

export type OverallStatus = "PASS" | "PASS_WITH_WARNINGS" | "BLOCKED";
export type DatasetValidationStatus = "PASS" | "PASS_WITH_WARNINGS" | "FAIL" | "NOT_RETRIEVED";

export interface CommonPeriod {
  first: string;
  last: string;
  price_dates: number;
  return_observations: number;
  session_coverage: number | null;
}

export interface DatasetStatus {
  dataset_id: string;
  name: string;
  role: "portfolio_asset" | "benchmark" | "risk_free" | "cross_check" | "calendar_reference";
  critical: boolean;
  status: DatasetValidationStatus;
  source: string;
  identifier: string;
  frequency: string;
  first_date: string | null;
  last_date: string | null;
  observations: number | null;
  session_coverage: number | null;
  failures: string[];
  warnings: string[];
  known_limitations: string[];
}

export interface DataStatusResponse {
  ready: boolean;
  state: DatasetState;
  message: string;
  manifest_path: string;
  generated_at: string | null;
  study_start: string;
  study_end: string;
  overall_status: OverallStatus | null;
  pipeline_version: string | null;
  common_period: CommonPeriod | null;
  datasets: DatasetStatus[];
  critical_failures: string[];
  warnings: string[];
  known_limitations: string[];
}

export type AssetClass = "equity" | "government_bond" | "gold";

export interface Asset {
  id: string;
  name: string;
  asset_class: AssetClass;
  sector: string;
  instrument: string;
  symbol: string | null;
  source: string;
  verified: boolean;
  notes: string;
}

export interface ReferenceSeries {
  id: string;
  name: string;
  role: "benchmark" | "risk_free";
  symbol: string | null;
  source: string;
  verified: boolean;
  notes: string;
}

export interface AssetUniverseResponse {
  assets: Asset[];
  benchmark: ReferenceSeries;
  risk_free: ReferenceSeries;
}

/** Annualized decimals (0.12 == 12%), computed by the backend. */
export interface PortfolioMetrics {
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
}
