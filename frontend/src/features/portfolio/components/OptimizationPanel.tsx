import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { portfolioApi } from "@/features/portfolio/api";
import { OptimizationForm } from "@/features/portfolio/components/OptimizationForm";
import { OptimizationResult } from "@/features/portfolio/components/OptimizationResult";
import { ProfileComparison } from "@/features/portfolio/components/ProfileComparison";
import { RiskReturnChart } from "@/features/portfolio/components/RiskReturnChart";
import type { InvestorProfile, OptimizationResponse } from "@/features/portfolio/types";

export function OptimizationPanel({ dataReady }: { dataReady: boolean }) {
  const [profile, setProfile] = useState<InvestorProfile>("balanced");
  // Latest successful result per profile; a later failure never erases them.
  const [results, setResults] = useState<Partial<Record<InvestorProfile, OptimizationResponse>>>({});
  const optimize = useMutation({
    mutationFn: portfolioApi.optimize,
    onSuccess: (data) => setResults((prev) => ({ ...prev, [data.profile]: data })),
  });
  const current = results[profile];

  return (
    <>
      <Card
        title="Investor profile optimization"
        description="Constrained numerical optimization (SciPy SLSQP) on the same expected returns, covariance and risk-free rate as the Monte Carlo simulation."
      >
        <OptimizationForm
          dataReady={dataReady}
          pending={optimize.isPending}
          profile={profile}
          onProfileChange={(p) => {
            setProfile(p);
            optimize.reset();
          }}
          onSubmit={(r) => optimize.mutate(r)}
        />
        <div className="mt-6 space-y-6">
          {optimize.isPending && <LoadingState label="Optimizing…" />}
          {optimize.error && (
            <ErrorAlert
              title={current ? "Optimization did not complete — showing the previous result" : "Optimization did not complete"}
              error={optimize.error}
            />
          )}
          {current && <OptimizationResult result={current} />}
          {!current && !optimize.isPending && !optimize.error && dataReady && (
            <p className="text-sm text-ink-muted">Select a profile and run the optimization.</p>
          )}
        </div>
      </Card>
      {current && (
        <Card title="Risk-return view" description="Where the optimized portfolios sit relative to the simulated opportunity set and the exact frontier.">
          <RiskReturnChart results={results} selected={profile} />
        </Card>
      )}
      {Object.keys(results).length > 0 && (
        <Card title="Profile comparison" description="Latest optimized result for each profile, side by side.">
          <ProfileComparison results={results} />
        </Card>
      )}
    </>
  );
}
