import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SeriesStatistics } from "@/features/analytics/types";
import { formatPercent, formatPercentTick } from "@/lib/formatters";

interface AnnualizedBarsProps {
  series: SeriesStatistics[];
  metric: "annualized_return" | "annualized_volatility";
  title: string;
}

/** One measure per chart (no dual axes); the benchmark bar is muted and labeled. */
export function AnnualizedBars({ series, metric, title }: AnnualizedBarsProps) {
  const rows = series
    .filter((s) => s[metric] !== null)
    .map((s) => ({ id: s.role === "benchmark" ? `${s.series_id} (benchmark)` : s.series_id, value: s[metric] as number, benchmark: s.role === "benchmark" }));
  return (
    <figure>
      <figcaption className="mb-2 text-sm font-medium">{title}</figcaption>
      <div className="h-72" role="img" aria-label={`${title} by series`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barCategoryGap={6}>
            <CartesianGrid horizontal={false} stroke="var(--color-grid)" />
            <XAxis type="number" tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="id" width={130} tick={{ fontSize: 11, fill: "var(--color-ink)" }} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: "var(--color-surface-muted)" }}
              formatter={(v) => [formatPercent(Number(v)), title]}
              contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "var(--color-ink)" }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.id} fill={r.benchmark ? "var(--color-ink-muted)" : "var(--color-chart-1)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
