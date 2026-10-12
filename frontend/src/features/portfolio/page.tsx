import { PageHeader } from "@/components/common/PageHeader";
import { MonteCarloPanel } from "@/features/portfolio/components/MonteCarloPanel";
import { OptimizationPanel } from "@/features/portfolio/components/OptimizationPanel";
import { useDataStatus } from "@/hooks/useDataStatus";

export function PortfolioPage() {
  const status = useDataStatus();
  const ready = status.data?.ready ?? false;
  return (
    <>
      <PageHeader
        eyebrow="Objective 2"
        title="Multi-asset portfolio optimization"
        description="Long-only allocations across six equities, a government-bond ETF and a gold ETF. Monte Carlo simulation maps the opportunity set; constrained optimization finds the portfolio for each investor profile."
      />
      <div className="grid grid-cols-1 gap-6">
        <MonteCarloPanel dataReady={ready} />
        <OptimizationPanel dataReady={ready} />
      </div>
    </>
  );
}
