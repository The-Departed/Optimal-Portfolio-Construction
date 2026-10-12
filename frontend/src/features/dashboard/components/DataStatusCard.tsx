import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { IssueList } from "@/features/dashboard/components/IssueList";
import { OVERALL_BADGE, STATE_BADGE } from "@/features/dashboard/status";
import { useDataStatus } from "@/hooks/useDataStatus";
import { formatDate, formatDateTime, formatPercent } from "@/lib/formatters";

export function DataStatusCard() {
  const { data, isPending, error } = useDataStatus();

  return (
    <Card title="Dataset status" description="Analyses run only on a validated, processed dataset.">
      {isPending && <LoadingState label="Checking dataset status…" />}
      {error && <ErrorAlert title="Could not check dataset status" error={error} />}
      {data && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={STATE_BADGE[data.state].tone}>{STATE_BADGE[data.state].label}</StatusBadge>
            {data.overall_status && (
              <StatusBadge tone={OVERALL_BADGE[data.overall_status].tone}>
                {`Validation: ${OVERALL_BADGE[data.overall_status].label}`}
              </StatusBadge>
            )}
          </div>
          <p className="text-sm">{data.message}</p>
          <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-ink-muted">Requested period</dt>
              <dd className="font-medium">
                {formatDate(data.study_start)} – {formatDate(data.study_end)}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">Common sample</dt>
              <dd className="font-medium">
                {data.common_period
                  ? `${formatDate(data.common_period.first)} – ${formatDate(data.common_period.last)}`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">Daily return observations</dt>
              <dd className="font-medium">
                {data.common_period
                  ? `${data.common_period.return_observations.toLocaleString("en-IN")}${
                      data.common_period.session_coverage !== null
                        ? ` (${formatPercent(data.common_period.session_coverage)} of sessions)`
                        : ""
                    }`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">Generated</dt>
              <dd className="font-medium">{data.generated_at ? formatDateTime(data.generated_at) : "—"}</dd>
            </div>
          </dl>
          <IssueList title="Critical failures" tone="negative" items={data.critical_failures} open />
          <IssueList title="Warnings" tone="warning" items={data.warnings} />
          <IssueList title="Known limitations" tone="neutral" items={data.known_limitations} />
          <p className="text-xs text-ink-muted">
            Full report: <span className="font-mono">data/reports/data_quality_report.md</span>
          </p>
        </div>
      )}
    </Card>
  );
}
