import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ChecksList } from "@/features/analytics/components/ChecksList";
import type { AnalyticsSummary } from "@/features/analytics/types";
import { formatDate, formatDateTime, formatInteger } from "@/lib/formatters";

const TONE = { PASS: "positive", PASS_WITH_WARNINGS: "warning", FAILED: "negative" } as const;

export function SampleOverview({ summary }: { summary: AnalyticsSummary }) {
  const { sample } = summary;
  return (
    <Card
      title="Sample and validation"
      description="All statistics below use the validated common sample unless stated otherwise."
      actions={<StatusBadge tone={TONE[summary.status]}>{`Analytics: ${summary.status.replaceAll("_", " ")}`}</StatusBadge>}
    >
      <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-ink-muted">Return period</dt>
          <dd className="font-medium">
            {formatDate(sample.start)} – {formatDate(sample.end)}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">Daily return observations</dt>
          <dd className="font-medium">{formatInteger(sample.observations)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Returns spanning &gt;1 session</dt>
          <dd className="font-medium">{formatInteger(sample.multi_session_returns)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Computed</dt>
          <dd className="font-medium">{formatDateTime(summary.computed_at)}</dd>
        </div>
      </dl>
      <details className="mt-4 rounded-lg border border-border px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium">Validation checks ({summary.checks.length})</summary>
        <div className="mt-3">
          <ChecksList checks={summary.checks} />
        </div>
      </details>
      <p className="mt-4 text-xs text-ink-muted">{summary.disclaimer}</p>
    </Card>
  );
}
