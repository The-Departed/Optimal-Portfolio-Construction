import { useQuery } from "@tanstack/react-query";
import { capmApi } from "@/features/capm/api";
import { queryKeys } from "@/lib/query-keys";

export function useCapmSummary() {
  return useQuery({ queryKey: queryKeys.capmSummary, queryFn: capmApi.summary, retry: false });
}
