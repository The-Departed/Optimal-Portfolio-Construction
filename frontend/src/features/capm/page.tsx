import { Card } from "@/components/common/Card";
import { PageHeader } from "@/components/common/PageHeader";
import { RequireData } from "@/components/common/RequireData";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { CapmMethodology } from "@/features/capm/components/CapmMethodology";
import { CapmResults } from "@/features/capm/components/CapmResults";

export function CapmPage() {
  return (
    <>
      <PageHeader
        eyebrow="Objective 1"
        title="CAPM equity evaluation"
        description="Market beta, CAPM-implied expected return, Jensen's alpha and regression diagnostics for six NSE-listed equities relative to NIFTY 50."
      />
      <div className="grid grid-cols-1 gap-6">
        <CapmMethodology />
        <Card title="Equity results" description="Descriptive statistics and CAPM estimates per equity.">
          <RequireData>
            <CapmResults />
          </RequireData>
        </Card>
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartFrame
            title="Historical vs CAPM-implied return"
            description="Annualized realized return against the CAPM expectation for each equity."
          />
          <ChartFrame
            title="Security characteristic line"
            description="Equity excess returns regressed on market excess returns."
          />
        </div>
      </div>
    </>
  );
}
