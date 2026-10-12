import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { DataStatusResponse } from "@/types/api";

export function useDataStatus() {
  return useQuery({
    queryKey: queryKeys.dataStatus,
    queryFn: () => apiClient.get<DataStatusResponse>("/data/status"),
  });
}
