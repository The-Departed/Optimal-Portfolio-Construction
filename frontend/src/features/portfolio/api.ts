import { apiClient } from "@/lib/api-client";
import type {
  FrontierResponse,
  OptimizationRequest,
  OptimizationResponse,
  ProfileDefinition,
  SimulationRequest,
  SimulationResponse,
} from "@/features/portfolio/types";

export const portfolioApi = {
  profiles: () => apiClient.get<ProfileDefinition[]>("/portfolio/profiles"),
  simulate: (body: SimulationRequest) => apiClient.post<SimulationResponse>("/portfolio/simulate", body),
  optimize: (body: OptimizationRequest) =>
    apiClient.post<OptimizationResponse>("/portfolio/optimize", body),
  frontier: (points = 30) => apiClient.get<FrontierResponse>(`/portfolio/frontier?points=${points}`),
};
