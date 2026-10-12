import { LineChart, PieChart } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { AnalyticsReadinessCard } from "@/features/dashboard/components/AnalyticsReadinessCard";
import { AssetUniverseTable } from "@/features/dashboard/components/AssetUniverseTable";
import { DatasetQualityTable } from "@/features/dashboard/components/DatasetQualityTable";
import { DataStatusCard } from "@/features/dashboard/components/DataStatusCard";
import { ModuleCard } from "@/features/dashboard/components/ModuleCard";

export function DashboardPage() {
  return (
    <>
      <PageHeader
        eyebrow="Financial engineering project"
        title="CAPM Equity Evaluation & Multi-Asset Portfolio Optimization"
        description="Evaluate six Indian equities against NIFTY 50 using the Capital Asset Pricing Model, then construct long-only portfolios across equities, government bonds and gold with Modern Portfolio Theory, Monte Carlo simulation and constrained optimization."
      />
      <div className="grid grid-cols-1 gap-6">
        <DataStatusCard />
        <AnalyticsReadinessCard />
        <DatasetQualityTable />
        <div className="grid gap-6 md:grid-cols-2">
          <ModuleCard
            to="/capm"
            icon={LineChart}
            title="CAPM equity evaluation"
            description="Beta, Jensen's alpha, CAPM-implied expected return and regression diagnostics for each equity."
          />
          <ModuleCard
            to="/portfolio"
            icon={PieChart}
            title="Portfolio optimization"
            description="Conservative, balanced and growth-oriented allocations across all eight assets."
          />
        </div>
        <AssetUniverseTable />
      </div>
    </>
  );
}
