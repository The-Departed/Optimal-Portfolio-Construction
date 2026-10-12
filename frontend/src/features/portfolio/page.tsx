import { Card } from "@/components/common/Card";
import { PageHeader } from "@/components/common/PageHeader";
import { MonteCarloPanel } from "@/features/portfolio/components/MonteCarloPanel";
import { OptimizationForm } from "@/features/portfolio/components/OptimizationForm";
import { useDataStatus } from "@/hooks/useDataStatus";

export function PortfolioPage() {
  const status = useDataStatus();
  const ready = status.data?.ready ?? false;
  return (
    <>
      <PageHeader
        eyebrow="Objective 2"
        title="Multi-asset portfolio optimization"
        description="Long-only allocations across six equities, a government-bond ETF and a gold ETF. Monte Carlo simulation maps the opportunity set; constrained optimization for each investor profile follows in Phase 6."
      />
      <div className="grid grid-cols-1 gap-6">
        <MonteCarloPanel dataReady={ready} />
        <Card title="Investor profile optimization" description="Constrained numerical optimization is implemented in Phase 6; requests currently return 'not implemented'.">
          <OptimizationForm dataReady={ready} />
        </Card>
      </div>
    </>
  );
}
