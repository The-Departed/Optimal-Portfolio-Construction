export const queryKeys = {
  health: ["health"] as const,
  dataStatus: ["data-status"] as const,
  assets: ["assets"] as const,
  profiles: ["portfolio", "profiles"] as const,
  capmSummary: ["capm", "summary"] as const,
  analyticsSummary: ["analytics", "summary"] as const,
  analyticsStatistics: (sample: string) => ["analytics", "statistics", sample] as const,
  analyticsCorrelation: ["analytics", "correlation"] as const,
  analyticsDistribution: (series: string, sample: string) =>
    ["analytics", "distribution", series, sample] as const,
  analyticsRiskFree: ["analytics", "risk-free"] as const,
};
