import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AssetWeight } from "@/features/portfolio/types";
import { formatPercent, formatPercentTick } from "@/lib/formatters";

export function AllocationChart({ weights, title }: { weights: AssetWeight[]; title: string }) {
  return (
    <figure>
      <figcaption className="mb-2 text-sm font-medium">{title}</figcaption>
      <div className="h-64" role="img" aria-label={`${title}: weight by asset`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={weights} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barCategoryGap={6}>
            <CartesianGrid horizontal={false} stroke="var(--color-grid)" />
            <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="asset_id" width={92} tick={{ fontSize: 11, fill: "var(--color-ink)" }} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: "var(--color-surface-muted)" }}
              formatter={(v) => [formatPercent(Number(v)), "Weight"]}
              contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "var(--color-ink)" }}
            />
            <Bar dataKey="weight" fill="var(--color-chart-1)" radius={[0, 4, 4, 0]} maxBarSize={16} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
