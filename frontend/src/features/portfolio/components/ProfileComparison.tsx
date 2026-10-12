import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { InvestorProfile, OptimizationResponse } from "@/features/portfolio/types";
import { formatFixed2, formatPercent, formatPercentTick, orDash } from "@/lib/formatters";

const ORDER: InvestorProfile[] = ["conservative", "balanced", "growth"];

export function ProfileComparison({ results }: { results: Partial<Record<InvestorProfile, OptimizationResponse>> }) {
  const runs = ORDER.map((p) => results[p]).filter((r): r is OptimizationResponse => Boolean(r));
  if (runs.length < 2) {
    return <p className="text-sm text-ink-muted">Optimize at least two profiles to compare them side by side.</p>;
  }
  const assets = runs[0]!.portfolio.weights.map((w) => w.asset_id);
  const chart = runs.map((r) => ({ name: r.label, ret: r.portfolio.expected_return, vol: r.portfolio.volatility }));
  return (
    <div className="space-y-6">
      <div className="h-64" role="img" aria-label="Expected return and volatility by profile">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chart} margin={{ left: 0, right: 8, top: 8, bottom: 4 }} barGap={2} barCategoryGap="30%">
            <CartesianGrid vertical={false} stroke="var(--color-grid)" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--color-ink)" }} tickLine={false} />
            <YAxis tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={44} />
            <Tooltip formatter={(v, name) => [formatPercent(Number(v)), name]} cursor={{ fill: "var(--color-surface-muted)" }}
              contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} labelStyle={{ color: "var(--color-ink)" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => <span style={{ color: "var(--color-ink-muted)" }}>{value}</span>} />
            <Bar dataKey="ret" name="Expected return (annualized)" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="vol" name="Volatility (annualized)" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="-mx-5 overflow-x-auto">
        <table className="w-full min-w-[40rem] text-right text-sm tabular-nums">
          <caption className="sr-only">Optimized profiles side by side</caption>
          <thead className="border-y border-border bg-surface-muted text-xs text-ink-muted">
            <tr>
              <th scope="col" className="px-5 py-2 text-left font-medium">Metric / asset</th>
              {runs.map((r) => (
                <th key={r.profile} scope="col" className="px-5 py-2 font-medium">
                  {r.label}
                  {r.max_volatility !== null && <span className="block font-normal">σ ≤ {formatPercent(r.max_volatility)}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <tr><th scope="row" className="px-5 py-2 text-left font-normal">Expected return</th>{runs.map((r) => <td key={r.profile} className="px-5 py-2 font-medium">{formatPercent(r.portfolio.expected_return)}</td>)}</tr>
            <tr><th scope="row" className="px-5 py-2 text-left font-normal">Volatility</th>{runs.map((r) => <td key={r.profile} className="px-5 py-2 font-medium">{formatPercent(r.portfolio.volatility)}</td>)}</tr>
            <tr><th scope="row" className="px-5 py-2 text-left font-normal">Sharpe ratio</th>{runs.map((r) => <td key={r.profile} className="px-5 py-2 font-medium">{orDash(r.portfolio.sharpe_ratio, formatFixed2)}</td>)}</tr>
            {assets.map((a, i) => (
              <tr key={a}>
                <th scope="row" className="px-5 py-1.5 text-left font-normal text-ink-muted">{a}</th>
                {runs.map((r) => <td key={r.profile} className="px-5 py-1.5">{formatPercent(r.portfolio.weights[i]!.weight)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
