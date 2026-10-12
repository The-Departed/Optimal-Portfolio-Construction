// Mirrors backend/app/schemas/capm.py. All returns are annualized decimals.

export interface CapmRegressionDiagnostics {
  observations: number;
  alpha_t_stat: number;
  alpha_p_value: number;
  beta_t_stat: number;
  beta_p_value: number;
  beta_std_error: number;
  durbin_watson: number;
}

export interface CapmEquityResult {
  asset_id: string;
  annualized_return: number;
  annualized_volatility: number;
  beta: number;
  capm_expected_return: number;
  jensens_alpha: number;
  r_squared: number;
  diagnostics: CapmRegressionDiagnostics;
}

export interface CapmSummaryResponse {
  risk_free_rate: number;
  market_return: number;
  equities: CapmEquityResult[];
}
