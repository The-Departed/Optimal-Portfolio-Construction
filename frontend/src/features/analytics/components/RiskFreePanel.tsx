import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useRiskFree } from "@/features/analytics/hooks/useAnalytics";
import { formatDate, formatFixed2, formatInteger } from "@/lib/formatters";

export function RiskFreePanel() {
  const { data, isPending, error } = useRiskFree();
  const points = data?.observations.filter((o) => o.in_study_period) ?? [];
  const p = data?.profile;
  // One tick per calendar year: the first auction date of each year.
  const yearTicks = points
    .filter((o, i) => i === 0 || o.auction_date.slice(0, 4) !== points[i - 1]!.auction_date.slice(0, 4))
    .map((o) => o.auction_date);
  return (
    <Card
      title="Risk-free rate (inspection only)"
      description="Native weekly observations. No daily risk-free series is derived until the conversion convention is approved."
      actions={<StatusBadge tone="warning">Conversion pending approval</StatusBadge>}
    >
      {isPending && <LoadingState label="Loading risk-free series…" />}
      {error && <ErrorAlert title="Risk-free series unavailable" error={error} />}
      {data?.error && <ErrorAlert title="Unsupported yield convention" error={new Error(data.error)} />}
      {p && (
        <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
          <figure>
            <figcaption className="sr-only">91-day T-bill implicit yield at cut-off, percent per annum</figcaption>
            <div className="h-56" role="img" aria-label="91-day T-bill auction yields over time">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={points} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-grid)" />
                  <XAxis dataKey="auction_date" ticks={yearTicks} tickFormatter={(d: string) => d.slice(0, 4)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} tickLine={false} />
                  <YAxis unit="%" domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={44} />
                  <Tooltip
                    labelFormatter={(d) => `Auction ${formatDate(String(d))}`}
                    formatter={(v) => [`${Number(v).toFixed(4)}% p.a.`, "Implicit yield"]}
                    contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
                  />
                  <Line type="stepAfter" dataKey="implicit_yield_pct" stroke="var(--color-chart-1)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </figure>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-ink-muted">Measure</dt><dd>{p.measure}</dd></div>
            <div><dt className="text-ink-muted">Units</dt><dd>{p.units}, {p.day_count}</dd></div>
            <div><dt className="text-ink-muted">Frequency</dt><dd>{p.frequency} (median gap {p.median_gap_days} days, max {p.max_gap_days})</dd></div>
            <div><dt className="text-ink-muted">Auctions in study period</dt><dd>{formatInteger(p.observations)} ({formatDate(p.first_date)} – {formatDate(p.last_date)})</dd></div>
            <div><dt className="text-ink-muted">Range</dt><dd>{formatFixed2(p.min_yield_pct)}% – {formatFixed2(p.max_yield_pct)}% p.a.</dd></div>
          </dl>
          <p className="text-xs text-ink-muted lg:col-span-2">Proposed conversion: {p.proposed_conversion}</p>
        </div>
      )}
    </Card>
  );
}
