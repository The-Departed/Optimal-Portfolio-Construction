import { PageHeader } from "@/components/common/PageHeader";
import { RequireData } from "@/components/common/RequireData";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { Card } from "@/components/common/Card";
import { AnnualizedBars } from "@/features/analytics/components/AnnualizedBars";
import { CorrelationHeatmap } from "@/features/analytics/components/CorrelationHeatmap";
import { ReturnDistribution } from "@/features/analytics/components/ReturnDistribution";
import { RiskFreePanel } from "@/features/analytics/components/RiskFreePanel";
import { SampleOverview } from "@/features/analytics/components/SampleOverview";
import { StatisticsTable } from "@/features/analytics/components/StatisticsTable";
import { useAnalyticsSummary, useStatistics } from "@/features/analytics/hooks/useAnalytics";

function AnalyticsContent() {
  const summary = useAnalyticsSummary();
  const stats = useStatistics("common");
  if (summary.isPending) return <LoadingState label="Computing descriptive analytics…" />;
  if (summary.error) return <ErrorAlert title="Descriptive analytics unavailable" error={summary.error} />;
  const ids = [...summary.data.assets, summary.data.benchmark];
  return (
    <div className="grid grid-cols-1 gap-6">
      <SampleOverview summary={summary.data} />
      <StatisticsTable />
      {stats.data && (
        <Card title="Historical annualized return and volatility" description="Common sample. Historical estimates, not forecasts.">
          <div className="grid gap-6 lg:grid-cols-2">
            <AnnualizedBars series={stats.data.series} metric="annualized_return" title="CAGR (compound annual growth rate)" />
            <AnnualizedBars series={stats.data.series} metric="annualized_volatility" title="Annualized volatility" />
          </div>
        </Card>
      )}
      <CorrelationHeatmap />
      <ReturnDistribution seriesIds={ids} />
      <RiskFreePanel />
    </div>
  );
}

export function AnalyticsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Descriptive analytics"
        title="Returns, risk and correlation"
        description="Daily simple returns, descriptive statistics and the dependence structure of the eight portfolio assets and NIFTY 50, computed by the backend from the validated dataset."
      />
      <RequireData>
        <AnalyticsContent />
      </RequireData>
    </>
  );
}
