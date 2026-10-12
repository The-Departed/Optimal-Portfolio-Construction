// Metadata fixtures only — no financial results.
import type { ProfileDefinition } from "@/features/portfolio/types";
import type { AssetUniverseResponse, DataStatusResponse } from "@/types/api";

export const dataMissing: DataStatusResponse = {
  ready: false,
  state: "missing",
  message: "No processed dataset found. Data acquisition has not been run yet.",
  manifest_path: "data/processed/manifest.json",
  generated_at: null,
  study_start: "2019-01-01",
  study_end: "2025-12-31",
  overall_status: null,
  pipeline_version: null,
  common_period: null,
  datasets: [],
  critical_failures: [],
  warnings: [],
  known_limitations: [],
};

// Readiness metadata only: no prices, returns or financial results.
export const dataReady: DataStatusResponse = {
  ...dataMissing,
  ready: true,
  state: "ready",
  message: "Validated dataset available with documented warnings and limitations.",
  generated_at: "2026-10-12T12:33:21Z",
  overall_status: "PASS_WITH_WARNINGS",
  pipeline_version: "2.0.0",
  common_period: { first: "2019-01-02", last: "2025-12-31", price_dates: 1690, return_observations: 1689, session_coverage: 0.9769 },
  datasets: [
    {
      dataset_id: "GSEC",
      name: "Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt",
      role: "portfolio_asset",
      critical: true,
      status: "PASS_WITH_WARNINGS",
      source: "AMFI NAV history",
      identifier: "139496",
      frequency: "daily",
      first_date: "2019-01-01",
      last_date: "2025-12-31",
      observations: 1698,
      session_coverage: 1,
      failures: [],
      warnings: ["expected_non_valuation_days: 36 NSE sessions without NAV"],
      known_limitations: [],
    },
  ],
  warnings: ["GOLD: source_errors: 2 records excluded"],
  known_limitations: ["NIFTY50: Price index, not the Total Return Index"],
};

export const dataBlocked: DataStatusResponse = {
  ...dataReady,
  ready: false,
  state: "validation_failed",
  message: "The dataset is BLOCKED by failed validation checks.",
  overall_status: "BLOCKED",
  critical_failures: ["RF_TBILL_91D: not retrieved (network failure)"],
};

export const universe: AssetUniverseResponse = {
  assets: [
    {
      id: "TCS",
      name: "Tata Consultancy Services",
      asset_class: "equity",
      sector: "IT services",
      instrument: "Listed equity (NSE)",
      symbol: "TCS.NS",
      source: "Yahoo Finance",
      verified: false,
      notes: "",
    },
  ],
  benchmark: { id: "NIFTY50", name: "NIFTY 50", role: "benchmark", symbol: "^NSEI", source: "Yahoo Finance", verified: false, notes: "" },
  risk_free: { id: "RF", name: "Short-term Indian government yield", role: "risk_free", symbol: null, source: "RBI DBIE", verified: false, notes: "" },
};

export const profiles: ProfileDefinition[] = [
  { profile: "conservative", label: "Conservative", objective: "Minimize volatility.", formulation: "minimize sqrt(w' Sigma w)", requires_max_volatility: false },
  { profile: "balanced", label: "Balanced", objective: "Maximize Sharpe.", formulation: "maximize sharpe", requires_max_volatility: false },
  { profile: "growth", label: "Growth-oriented", objective: "Maximize return.", formulation: "maximize w' mu", requires_max_volatility: true },
];
