import { BarChart3 } from "lucide-react";
import { Link } from "react-router";
import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useAnalyticsSummary } from "@/features/analytics/hooks/useAnalytics";
import { useDataStatus } from "@/hooks/useDataStatus";
import { formatDate, formatInteger } from "@/lib/formatters";

const TONE = { PASS: "positive", PASS_WITH_WARNINGS: "positive", FAILED: "negative" } as const;
const LABEL = { PASS: "Validated", PASS_WITH_WARNINGS: "Validated", FAILED: "Failed" } as const;

export function AnalyticsReadinessCard() {
  const status = useDataStatus();
  const ready = status.data?.ready ?? false;
  const summary = useAnalyticsSummary();
  if (!ready) return null;

  return (
    <Card title="Descriptive analytics" description="Returns, statistics and correlation computed from the validated dataset.">
      {summary.isPending && <p className="text-sm text-ink-muted">Computing analytics…</p>}
      {summary.error && (
        <div className="space-y-1">
          <StatusBadge tone="negative">Unavailable</StatusBadge>
          <p className="text-sm text-ink-muted">{summary.error.message}</p>
        </div>
      )}
      {summary.data && (
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <StatusBadge tone={TONE[summary.data.status]}>{`Analytics: ${LABEL[summary.data.status]}`}</StatusBadge>
            <p className="text-sm text-ink-muted">
              {formatInteger(summary.data.sample.observations)} daily returns, {formatDate(summary.data.sample.start)} –{" "}
              {formatDate(summary.data.sample.end)}
            </p>
          </div>
          <Link to="/analytics" className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline">
            <BarChart3 aria-hidden className="size-4" /> Open descriptive analytics
          </Link>
        </div>
      )}
    </Card>
  );
}
