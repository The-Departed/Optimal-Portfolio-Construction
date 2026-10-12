import { useMutation } from "@tanstack/react-query";
import { portfolioApi } from "@/features/portfolio/api";

export function useSimulation() {
  return useMutation({ mutationFn: portfolioApi.simulate });
}
