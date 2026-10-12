import { useMutation } from "@tanstack/react-query";
import { portfolioApi } from "@/features/portfolio/api";

export function useOptimizePortfolio() {
  return useMutation({ mutationFn: portfolioApi.optimize });
}
