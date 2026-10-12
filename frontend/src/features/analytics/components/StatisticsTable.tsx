import { useState } from "react";
import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { SegmentedControl } from "@/components/common/SegmentedControl";
import { useStatistics } from "@/features/analytics/hooks/useAnalytics";
import type { Sample, SeriesStatistics } from "@/features/analytics/types";
import { formatFixed2, formatInteger, formatPercent, formatPercentPrecise, orDash } from "@/lib/formatters";

type Column = { key: keyof SeriesStatistics; label: string; fmt: (v: number) => string; group: "Daily" | "Shape" | "Annualized" };

const COLUMNS: Column[] = [
  { key: "mean_daily", label: "Mean", fmt: formatPercentPrecise, group: "Daily" },
  { key: "median_daily", label: "Median", fmt: formatPercentPrecise, group: "Daily" },
  { key: "std_daily", label: "Std dev", fmt: formatPercentPrecise, group: "Daily" },
  { key: "min_daily", label: "Min", fmt: formatPercent, group: "Daily" },
  { key: "max_daily", label: "Max", fmt: formatPercent, group: "Daily" },
  { key: "skewness", label: "Skewness", fmt: formatFixed2, group: "Shape" },
  { key: "excess_kurtosis", label: "Excess kurtosis", fmt: formatFixed2, group: "Shape" },
  { key: "cumulative_return", label: "Cumulative", fmt: formatPercent, group: "Annualized" },
  { key: "annualized_return", label: "CAGR", fmt: formatPercent, group: "Annualized" },
  { key: "annualized_volatility", label: "Volatility", fmt: formatPercent, group: "Annualized" },
];

export function StatisticsTable() {
  const [sample, setSample] = useState<Sample>("common");
  const { data, isPending, error } = useStatistics(sample);

  return (
    <Card
      title="Descriptive statistics"
      description="Daily simple returns. Cumulative return and CAGR use the sample's first and last prices; volatility = daily std dev × √252."
      actions={
        <SegmentedControl
          label="Sample"
          value={sample}
          onChange={setSample}
          options={[
            { value: "common", label: "Common sample" },
            { value: "individual", label: "Each series' own history" },
          ]}
        />
      }
    >
      {isPending && <LoadingState label="Loading statistics…" />}
      {error && <ErrorAlert title="Statistics unavailable" error={error} />}
      {data && (
        <>
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full min-w-[64rem] text-right text-sm tabular-nums">
              <caption className="sr-only">Descriptive statistics of daily returns, {sample} sample</caption>
              <thead className="border-y border-border bg-surface-muted text-xs text-ink-muted">
                <tr>
                  <th scope="col" className="px-5 py-2 text-left font-medium" rowSpan={2}>Series</th>
                  <th scope="col" className="px-3 py-2 font-medium" rowSpan={2}>Obs.</th>
                  <th scope="colgroup" colSpan={5} className="px-3 pt-2 text-center font-medium uppercase tracking-wide">Daily</th>
                  <th scope="colgroup" colSpan={2} className="px-3 pt-2 text-center font-medium uppercase tracking-wide">Shape</th>
                  <th scope="colgroup" colSpan={3} className="px-5 pt-2 text-center font-medium uppercase tracking-wide">Whole period / annualized</th>
                </tr>
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} scope="col" className="px-3 pb-2 font-medium">{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.series.map((s) => (
                  <tr key={s.series_id} className={s.role === "benchmark" ? "bg-surface-muted/60" : undefined}>
                    <th scope="row" className="px-5 py-2.5 text-left font-normal">
                      <span className="font-medium">{s.series_id}</span>
                      {s.role === "benchmark" && <span className="ml-1.5 text-xs text-ink-muted">benchmark</span>}
                      <span className="block whitespace-nowrap text-xs text-ink-muted">
                        {s.start} – {s.end}
                      </span>
                    </th>
                    <td className="px-3 py-2.5">{formatInteger(s.observations)}</td>
                    {COLUMNS.map((c) => (
                      <td key={c.key} className="px-3 py-2.5" title={s.notes.join("\n") || undefined}>
                        {orDash(s[c.key] as number | null, c.fmt)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-ink-muted">
            Skewness: adjusted Fisher–Pearson G1. Excess kurtosis: sample-adjusted G2 (normal = 0). Std dev uses ddof = 1.
            CAGR = (P_end / P_start)^(365.25 / days) − 1, which differs from mean daily return × 252.
            {sample === "individual" &&
              " Individual samples use each series' own validated dates, so they differ from the common sample used for correlation and covariance."}
          </p>
        </>
      )}
    </Card>
  );
}
