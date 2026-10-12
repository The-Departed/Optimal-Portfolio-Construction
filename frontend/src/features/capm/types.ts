// Mirrors backend/app/schemas/capm.py. Returns are decimals (0.12 == 12%).

export interface CapmDiagnostics {
  intercept_daily: number;
  intercept_std_error: number;
  intercept_t_stat: number;
  intercept_p_value: number;
  intercept_hac_p_value: number;
  intercept_ci_low: number;
  intercept_ci_high: number;
  beta_std_error: number;
  beta_t_stat: number;
  beta_p_value: number;
  beta_ci_low: number;
  beta_ci_high: number;
  beta_hac_std_error: number;
  beta_hac_p_value: number;
  hac_lags: number;
  adj_r_squared: number;
  residual_std_daily: number;
  residual_volatility_annualized: number;
  durbin_watson: number;
}

export interface CapmEquityResult {
  asset_id: string;
  name: string;
  sector: string;
  status: "ok" | "failed";
  error: string | null;
  observations: number | null;
  start: string | null;
  end: string | null;
  historical_cagr: number | null;
  historical_mean_return: number | null;
  annualized_volatility: number | null;
  beta: number | null;
  capm_expected_return: number | null;
  jensens_alpha: number | null;
  intercept_annualized: number | null;
  r_squared: number | null;
  diagnostics: CapmDiagnostics | null;
  warnings: string[];
}

export interface CapmSummaryResponse {
  status: "PASS" | "PASS_WITH_WARNINGS" | "FAILED";
  sample_start: string;
  sample_end: string;
  observations: number;
  periods_per_year: number;
  market: { series_id: string; mean_return: number; annualized_volatility: number; market_risk_premium: number };
  risk_free: {
    series_id: string;
    annualized_rate: number;
    mean_quoted_yield: number;
    convention: string;
    first_auction_used: string;
    last_auction_used: string;
    max_staleness_days: number;
  };
  definitions: Record<string, string>;
  equities: CapmEquityResult[];
  warnings: string[];
  disclaimer: string;
}
