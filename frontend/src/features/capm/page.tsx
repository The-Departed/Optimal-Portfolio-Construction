import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RequireData } from "@/components/common/RequireData";
import { BetaChart } from "@/features/capm/components/BetaChart";
import { CapmMethodology } from "@/features/capm/components/CapmMethodology";
import { CapmOverview } from "@/features/capm/components/CapmOverview";
import { CapmReturnChart } from "@/features/capm/components/CapmReturnChart";
import { CapmTable } from "@/features/capm/components/CapmTable";
import { EquityDetail } from "@/features/capm/components/EquityDetail";
import { useCapmSummary } from "@/features/capm/hooks/useCapmSummary";

function CapmContent() {
  const { data, isPending, error } = useCapmSummary();
  if (isPending) return <LoadingState label="Estimating CAPM regressions…" />;
  if (error) return <ErrorAlert title="CAPM analysis unavailable" error={error} />;
  return (
    <div className="grid grid-cols-1 gap-6">
      <CapmOverview data={data} />
      <CapmTable data={data} />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <CapmReturnChart data={data} />
        <BetaChart data={data} />
      </div>
      <EquityDetail data={data} />
    </div>
  );
}

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
        <RequireData>
          <CapmContent />
        </RequireData>
      </div>
    </>
  );
}
