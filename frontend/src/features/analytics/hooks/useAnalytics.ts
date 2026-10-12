import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/features/analytics/api";
import type { Sample } from "@/features/analytics/types";
import { queryKeys } from "@/lib/query-keys";

// Analytics only change when the dataset does; the backend caches per dataset version.
const STALE = 5 * 60 * 1000;

export const useAnalyticsSummary = () =>
  useQuery({ queryKey: queryKeys.analyticsSummary, queryFn: analyticsApi.summary, staleTime: STALE });

export const useStatistics = (sample: Sample) =>
  useQuery({
    queryKey: queryKeys.analyticsStatistics(sample),
    queryFn: () => analyticsApi.statistics(sample),
    staleTime: STALE,
  });

export const useCorrelation = () =>
  useQuery({ queryKey: queryKeys.analyticsCorrelation, queryFn: analyticsApi.correlation, staleTime: STALE });

export const useDistribution = (series: string, sample: Sample) =>
  useQuery({
    queryKey: queryKeys.analyticsDistribution(series, sample),
    queryFn: () => analyticsApi.distribution(series, sample),
    staleTime: STALE,
  });

export const useRiskFree = () =>
  useQuery({ queryKey: queryKeys.analyticsRiskFree, queryFn: analyticsApi.riskFree, staleTime: STALE });
