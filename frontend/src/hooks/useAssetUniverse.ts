import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { AssetUniverseResponse } from "@/types/api";

export function useAssetUniverse() {
  return useQuery({
    queryKey: queryKeys.assets,
    queryFn: () => apiClient.get<AssetUniverseResponse>("/assets"),
    staleTime: Infinity,
  });
}
