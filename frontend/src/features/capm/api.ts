import { apiClient } from "@/lib/api-client";
import type { CapmSummaryResponse } from "@/features/capm/types";

export const capmApi = {
  summary: () => apiClient.get<CapmSummaryResponse>("/capm/summary"),
};
