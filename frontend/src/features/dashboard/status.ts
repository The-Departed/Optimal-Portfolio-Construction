import type { DatasetState, DatasetValidationStatus, OverallStatus } from "@/types/api";

export type Tone = "neutral" | "positive" | "warning" | "negative";

export const STATE_BADGE: Record<DatasetState, { tone: Tone; label: string }> = {
  missing: { tone: "neutral", label: "No dataset" },
  invalid: { tone: "negative", label: "Artifacts invalid" },
  validation_failed: { tone: "negative", label: "Blocked" },
  ready: { tone: "positive", label: "Ready for analysis" },
};

export const OVERALL_BADGE: Record<OverallStatus, { tone: Tone; label: string }> = {
  PASS: { tone: "positive", label: "Validated" },
  PASS_WITH_WARNINGS: { tone: "positive", label: "Validated" },
  BLOCKED: { tone: "negative", label: "BLOCKED" },
};

export const DATASET_BADGE: Record<DatasetValidationStatus, { tone: Tone; label: string }> = {
  PASS: { tone: "positive", label: "Pass" },
  PASS_WITH_WARNINGS: { tone: "positive", label: "Pass" },
  FAIL: { tone: "negative", label: "Fail" },
  NOT_RETRIEVED: { tone: "negative", label: "Not retrieved" },
};

export const ROLE_LABEL: Record<string, string> = {
  portfolio_asset: "Portfolio asset",
  benchmark: "Benchmark",
  risk_free: "Risk-free rate",
  cross_check: "Cross-check",
  calendar_reference: "Calendar reference",
};
