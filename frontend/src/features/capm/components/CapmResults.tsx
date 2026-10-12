import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { useCapmSummary } from "@/features/capm/hooks/useCapmSummary";

/** Rendered only when the dataset is ready; full results UI arrives in Phase 7. */
export function CapmResults() {
  const { data, isPending, error } = useCapmSummary();
  if (isPending) return <LoadingState label="Running CAPM analysis…" />;
  if (error) return <ErrorAlert title="CAPM analysis unavailable" error={error} />;
  return <p className="text-sm text-ink-muted">{data.equities.length} equities evaluated.</p>;
}
