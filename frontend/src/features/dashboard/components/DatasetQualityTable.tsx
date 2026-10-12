import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DATASET_BADGE, ROLE_LABEL } from "@/features/dashboard/status";
import { useDataStatus } from "@/hooks/useDataStatus";
import { formatDate, formatPercent } from "@/lib/formatters";

export function DatasetQualityTable() {
  const { data } = useDataStatus();
  if (!data || data.datasets.length === 0) return null;

  return (
    <Card
      title="Dataset validation"
      description="Per-dataset coverage and validation status from the latest pipeline run. Cross-check and calendar datasets are never analysis inputs."
    >
      <div className="-mx-5 overflow-x-auto">
        <table className="w-full min-w-[48rem] text-left text-sm">
          <thead className="border-y border-border bg-surface-muted text-xs uppercase tracking-wide text-ink-muted">
            <tr>
              <th scope="col" className="px-5 py-2 font-medium">Dataset</th>
              <th scope="col" className="px-3 py-2 font-medium">Role</th>
              <th scope="col" className="px-3 py-2 font-medium">Coverage</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Obs.</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Sessions</th>
              <th scope="col" className="px-5 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.datasets.map((d) => {
              const issues = [...d.failures, ...d.warnings];
              return (
                <tr key={d.dataset_id} className="align-top">
                  <td className="px-5 py-2.5">
                    <p className="font-medium">{d.dataset_id}</p>
                    <p className="text-xs text-ink-muted">{d.name}</p>
                    <p className="text-xs text-ink-muted">
                      {d.source} · <span className="font-mono">{d.identifier}</span>
                    </p>
                  </td>
                  <td className="px-3 py-2.5 text-ink-muted">{ROLE_LABEL[d.role] ?? d.role}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {d.first_date && d.last_date
                      ? `${formatDate(d.first_date)} – ${formatDate(d.last_date)}`
                      : "—"}
                    <p className="text-xs text-ink-muted">{d.frequency}</p>
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums">
                    {d.observations?.toLocaleString("en-IN") ?? "—"}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums">
                    {d.session_coverage !== null ? formatPercent(d.session_coverage) : "—"}
                  </td>
                  <td className="px-5 py-2.5">
                    <StatusBadge tone={DATASET_BADGE[d.status].tone}>{DATASET_BADGE[d.status].label}</StatusBadge>
                    {issues.length > 0 && (
                      <details className="mt-1 text-xs text-ink-muted">
                        <summary className="cursor-pointer">
                          {issues.length} issue{issues.length > 1 ? "s" : ""}
                        </summary>
                        <ul className="mt-1 max-w-sm list-disc space-y-1 pl-4">
                          {issues.map((m) => (
                            <li key={m} className="break-words">
                              {m}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
