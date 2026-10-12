import type { CSSProperties } from "react";
import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { useCorrelation } from "@/features/analytics/hooks/useAnalytics";
import { formatDate, formatInteger } from "@/lib/formatters";

/** Diverging fill: blue for positive, red for negative, neutral gray at zero. */
function cellStyle(r: number): CSSProperties {
  const pole = r >= 0 ? "var(--color-div-pos)" : "var(--color-div-neg)";
  const weight = Math.round(Math.min(Math.abs(r), 1) * 100);
  return {
    background: `color-mix(in oklab, ${pole} ${weight}%, var(--color-div-mid))`,
    color: Math.abs(r) >= 0.55 ? "#ffffff" : "var(--color-ink)",
  };
}

export function CorrelationHeatmap() {
  const { data, isPending, error } = useCorrelation();
  return (
    <Card
      title="Correlation of daily returns"
      description="Pearson correlation on the common sample. Historical correlation does not guarantee future diversification."
    >
      {isPending && <LoadingState label="Loading correlation matrix…" />}
      {error && <ErrorAlert title="Correlation unavailable" error={error} />}
      {data && (
        <>
          <div className="-mx-5 overflow-x-auto px-5">
            <table className="mx-auto table-fixed border-separate border-spacing-0.5 text-xs tabular-nums">
              <caption className="sr-only">Correlation matrix of daily returns</caption>
              <thead>
                <tr>
                  <td className="w-24" />
                  {data.labels.map((l) => (
                    <th key={l} scope="col" className="w-16 px-0.5 pb-1 font-medium text-ink-muted" title={l}>
                      <span className="block truncate">{l}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.labels.map((row, i) => (
                  <tr key={row}>
                    <th scope="row" className="pr-2 text-right font-medium text-ink-muted">{row}</th>
                    {data.values[i]!.map((v, j) => (
                      <td
                        key={data.labels[j]}
                        title={`${row} vs ${data.labels[j]}: ${v.toFixed(4)} (n = ${data.pairwise_observations[i]![j]})`}
                        style={cellStyle(v)}
                        className="h-11 w-16 rounded text-center"
                      >
                        {v.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-ink-muted">
            <div className="flex items-center gap-2" aria-hidden>
              <span>−1</span>
              <span className="h-2.5 w-40 rounded" style={{ background: "linear-gradient(to right, var(--color-div-neg), var(--color-div-mid), var(--color-div-pos))" }} />
              <span>+1</span>
            </div>
            <span>
              {formatDate(data.start)} – {formatDate(data.end)} · n = {formatInteger(data.observations)} for every pair ·{" "}
              {data.diagnostics.valid ? "symmetric, positive semidefinite" : data.diagnostics.problems.join("; ")}
            </span>
          </div>
        </>
      )}
    </Card>
  );
}
