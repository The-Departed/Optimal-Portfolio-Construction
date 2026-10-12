import { useQuery } from "@tanstack/react-query";
import { portfolioApi } from "@/features/portfolio/api";

const STALE = 5 * 60 * 1000;

/** Exact long-only frontier (backend constrained optimization). */
export const useFrontier = (enabled: boolean) =>
  useQuery({ queryKey: ["portfolio", "frontier"], queryFn: () => portfolioApi.frontier(30), enabled, staleTime: STALE });

/** The Monte Carlo run used for the optimizer comparison (cached by the backend per n and seed). */
export const useComparisonSimulation = (n: number, seed: number, enabled: boolean) =>
  useQuery({
    queryKey: ["portfolio", "simulation", n, seed],
    queryFn: () => portfolioApi.simulate({ n_portfolios: n, seed, scatter_points: 1500 }),
    enabled,
    staleTime: STALE,
  });
