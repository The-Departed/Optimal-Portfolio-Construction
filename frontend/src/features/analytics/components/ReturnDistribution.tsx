import { useId, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { useDistribution } from "@/features/analytics/hooks/useAnalytics";
import { formatInteger, formatPercent, formatPercentPrecise, formatPercentTick, orDash } from "@/lib/formatters";

export function ReturnDistribution({ seriesIds }: { seriesIds: string[] }) {
  const [series, setSeries] = useState(seriesIds[0] ?? "");
  const selectId = useId();
  const { data, isPending, error } = useDistribution(series, "common");
  const bins =
    data?.counts.map((count, i) => ({
      mid: (data.bin_edges[i]! + data.bin_edges[i + 1]!) / 2,
      range: `${formatPercent(data.bin_edges[i]!)} to ${formatPercent(data.bin_edges[i + 1]!)}`,
      count,
    })) ?? [];

  return (
    <Card
      title="Distribution of daily returns"
      description="Histogram of daily simple returns on the common sample (50 equal-width bins, computed by the backend)."
      actions={
        <div className="flex items-center gap-2 text-sm">
          <label htmlFor={selectId} className="text-ink-muted">Series</label>
          <select
            id={selectId}
            value={series}
            onChange={(e) => setSeries(e.target.value)}
            className="rounded-md border border-border bg-surface px-2 py-1"
          >
            {seriesIds.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      }
    >
      {isPending && <LoadingState label="Loading distribution…" />}
      {error && <ErrorAlert title="Distribution unavailable" error={error} />}
      {data && (
        <>
          <div className="h-64" role="img" aria-label={`Histogram of ${data.series_id} daily returns`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bins} margin={{ left: 0, right: 8, top: 4, bottom: 4 }} barCategoryGap={1}>
                <CartesianGrid vertical={false} stroke="var(--color-grid)" />
                <XAxis dataKey="mid" tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} minTickGap={24} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={40} />
                <Tooltip
                  cursor={{ fill: "var(--color-surface-muted)" }}
                  labelFormatter={(_, payload) => payload?.[0]?.payload?.range ?? ""}
                  formatter={(v) => [formatInteger(Number(v)), "Days"]}
                  contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="count" fill="var(--color-chart-1)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-ink-muted">
            {formatInteger(data.observations)} daily returns · mean {orDash(data.mean_daily, formatPercentPrecise)} · std dev{" "}
            {orDash(data.std_daily, formatPercentPrecise)} (daily)
          </p>
        </>
      )}
    </Card>
  );
}
