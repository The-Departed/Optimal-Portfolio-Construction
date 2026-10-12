import { apiClient } from "@/lib/api-client";
import type {
  AnalyticsSummary,
  DistributionResponse,
  MatrixResponse,
  RiskFreeResponse,
  Sample,
  StatisticsResponse,
} from "@/features/analytics/types";

export const analyticsApi = {
  summary: () => apiClient.get<AnalyticsSummary>("/analytics/summary"),
  statistics: (sample: Sample) => apiClient.get<StatisticsResponse>(`/analytics/statistics?sample=${sample}`),
  correlation: () => apiClient.get<MatrixResponse>("/analytics/correlation"),
  distribution: (series: string, sample: Sample) =>
    apiClient.get<DistributionResponse>(
      `/analytics/distribution?series=${encodeURIComponent(series)}&sample=${sample}&bins=50`,
    ),
  riskFree: () => apiClient.get<RiskFreeResponse>("/analytics/risk-free"),
};
