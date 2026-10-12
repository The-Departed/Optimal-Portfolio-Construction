import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/common/Card";
import type { CapmSummaryResponse } from "@/features/capm/types";
import { formatPercent, formatPercentTick } from "@/lib/formatters";

export function CapmReturnChart({ data }: { data: CapmSummaryResponse }) {
  const rows = data.equities
    .filter((e) => e.status === "ok")
    .map((e) => ({ id: e.asset_id, historical: e.historical_mean_return, capm: e.capm_expected_return }));
  return (
    <Card
      title="Historical vs CAPM-implied annual return"
      description="The gap between the bars is Jensen's alpha. Historical, not a forecast."
    >
      <div className="h-80" role="img" aria-label="Historical mean return and CAPM expected return by equity">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 4 }} barGap={2} barCategoryGap="25%">
            <CartesianGrid vertical={false} stroke="var(--color-grid)" />
            <XAxis dataKey="id" tick={{ fontSize: 11, fill: "var(--color-ink)" }} tickLine={false} />
            <YAxis tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={48} />
            <Tooltip
              cursor={{ fill: "var(--color-surface-muted)" }}
              formatter={(v, name) => [formatPercent(Number(v)), name]}
              contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "var(--color-ink)" }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => <span style={{ color: "var(--color-ink-muted)" }}>{value}</span>} />
            <Bar dataKey="historical" name="Historical mean (annualized)" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="capm" name="CAPM expected return" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
