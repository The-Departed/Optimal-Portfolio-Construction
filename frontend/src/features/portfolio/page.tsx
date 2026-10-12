import { Card } from "@/components/common/Card";
import { PageHeader } from "@/components/common/PageHeader";
import { RequireData } from "@/components/common/RequireData";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { OptimizationForm } from "@/features/portfolio/components/OptimizationForm";
import { useDataStatus } from "@/hooks/useDataStatus";

export function PortfolioPage() {
  const status = useDataStatus();
  return (
    <>
      <PageHeader
        eyebrow="Objective 2"
        title="Multi-asset portfolio optimization"
        description="Long-only allocations across six equities, a government-bond ETF and a gold ETF. Monte Carlo simulation maps the opportunity set; a constrained optimizer finds each profile's allocation."
      />
      <div className="grid grid-cols-1 gap-6">
        <Card title="Investor profile" description="Select an objective. Weights satisfy Σw = 1 and 0 ≤ wᵢ ≤ 1.">
          <OptimizationForm dataReady={status.data?.ready ?? false} />
        </Card>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame
            title="Monte Carlo opportunity set"
            description="Simulated portfolios by annualized volatility and expected return, colored by Sharpe ratio."
          />
          <ChartFrame
            title="Efficient frontier"
            description="Frontier portfolios with the selected optimum highlighted."
          />
          <ChartFrame title="Asset allocation" description="Optimal weights by asset." />
          <Card title="Portfolio metrics" description="Expected return, volatility and Sharpe ratio.">
            <RequireData>
              <p className="text-sm text-ink-muted">Run an optimization to see results.</p>
            </RequireData>
          </Card>
        </div>
      </div>
    </>
  );
}
