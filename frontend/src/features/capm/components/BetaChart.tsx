import { Bar, BarChart, CartesianGrid, ErrorBar, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/common/Card";
import type { CapmSummaryResponse } from "@/features/capm/types";
import { formatFixed2 } from "@/lib/formatters";

export function BetaChart({ data }: { data: CapmSummaryResponse }) {
  const rows = data.equities
    .filter((e) => e.status === "ok" && e.beta !== null && e.diagnostics)
    .map((e) => ({
      id: e.asset_id,
      beta: e.beta as number,
      ci: [(e.beta as number) - e.diagnostics!.beta_ci_low, e.diagnostics!.beta_ci_high - (e.beta as number)],
      low: e.diagnostics!.beta_ci_low,
      high: e.diagnostics!.beta_ci_high,
    }));
  return (
    <Card
      title="Market beta with 95% confidence intervals"
      description="Beta (unitless) measures sensitivity to market excess returns: 1 moves with NIFTY 50, above 1 amplifies market moves, below 1 dampens them."
    >
      <div className="h-72" role="img" aria-label="Beta by equity with 95% confidence intervals">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 4 }} barCategoryGap="35%">
            <CartesianGrid vertical={false} stroke="var(--color-grid)" />
            <XAxis dataKey="id" interval={0} tick={{ fontSize: 10, fill: "var(--color-ink)" }} tickLine={false} />
            <YAxis domain={[0, "auto"]} tickFormatter={(v: number) => v.toFixed(1)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={32} />
            <ReferenceLine y={1} stroke="var(--color-ink-muted)" strokeDasharray="4 4" label={{ value: "β = 1 (market)", position: "insideTopRight", fontSize: 11, fill: "var(--color-ink-muted)" }} />
            <Tooltip
              cursor={{ fill: "var(--color-surface-muted)" }}
              content={({ active, payload }) => {
                const r = active ? (payload?.[0]?.payload as (typeof rows)[number] | undefined) : undefined;
                return r ? (
                  <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-sm">
                    <p className="font-medium">{r.id}</p>
                    <p>Beta {formatFixed2(r.beta)} (95% CI {formatFixed2(r.low)} – {formatFixed2(r.high)})</p>
                  </div>
                ) : null;
              }}
            />
            <Bar dataKey="beta" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              <ErrorBar dataKey="ci" width={6} strokeWidth={1.5} stroke="var(--color-ink)" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
