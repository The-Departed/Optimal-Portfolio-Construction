import { useQuery } from "@tanstack/react-query";
import { portfolioApi } from "@/features/portfolio/api";
import { queryKeys } from "@/lib/query-keys";

export function useProfiles() {
  return useQuery({ queryKey: queryKeys.profiles, queryFn: portfolioApi.profiles, staleTime: Infinity });
}
