import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { SimulationResponse } from "@/features/portfolio/types";
import { formatFixed2, formatPercent, formatPercentTick } from "@/lib/formatters";

type Point = { id: number; vol: number; ret: number; sharpe: number | null; kind: string };

function toPoints(set: SimulationResponse["scatter"], kind: string): Point[] {
  return set.portfolio_ids.map((id, i) => ({
    id,
    vol: set.volatilities[i]!,
    ret: set.expected_returns[i]!,
    sharpe: set.sharpe_ratios[i] ?? null,
    kind,
  }));
}

function PointTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  const p = active ? payload?.[0]?.payload : undefined;
  if (!p) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-sm">
      <p className="font-medium">{p.kind} · portfolio #{p.id}</p>
      <p>Expected return {formatPercent(p.ret)}</p>
      <p>Volatility {formatPercent(p.vol)}</p>
      <p>Sharpe {p.sharpe === null ? "—" : formatFixed2(p.sharpe)}</p>
    </div>
  );
}

export function OpportunitySetChart({ data }: { data: SimulationResponse }) {
  const sampled = toPoints(data.scatter, "Simulated");
  const frontier = toPoints(data.frontier, "Frontier approximation");
  const cand = (label: string) => {
    const c = data.candidates.find((x) => x.label === label);
    return c ? [{ id: c.portfolio_id, vol: c.volatility, ret: c.expected_return, sharpe: c.sharpe_ratio, kind: label === "min_volatility" ? "Min-volatility candidate" : "Max-Sharpe candidate" }] : [];
  };
  return (
    <figure>
      <figcaption className="sr-only">Annualized expected return against annualized volatility for simulated portfolios</figcaption>
      <div className="h-[26rem]" role="img" aria-label="Monte Carlo opportunity set">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ left: 4, right: 16, top: 8, bottom: 16 }}>
            <CartesianGrid stroke="var(--color-grid)" />
            <XAxis type="number" dataKey="vol" name="Volatility" domain={["auto", "auto"]} tickFormatter={(v: number) => formatPercentTick(v)}
              tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} tickLine={false}
              label={{ value: "Annualized volatility", position: "insideBottom", offset: -10, fontSize: 11, fill: "var(--color-ink-muted)" }} />
            <YAxis type="number" dataKey="ret" name="Expected return" domain={["auto", "auto"]} tickFormatter={(v: number) => formatPercentTick(v)}
              tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={48}
              label={{ value: "Expected return (annualized)", angle: -90, position: "insideLeft", offset: 10, fontSize: 11, fill: "var(--color-ink-muted)" }} />
            <ZAxis range={[14, 14]} />
            <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3" }} />
            <Legend verticalAlign="top" wrapperStyle={{ fontSize: 12, paddingBottom: 8 }} formatter={(value) => <span style={{ color: "var(--color-ink-muted)" }}>{value}</span>} />
            <Scatter name={`Simulated portfolios (${sampled.length.toLocaleString("en-IN")} of ${data.n_portfolios.toLocaleString("en-IN")} shown)`} data={sampled} fill="var(--color-chart-1)" fillOpacity={0.3} isAnimationActive={false} />
            <Scatter name="Monte Carlo frontier approximation" data={frontier} fill="var(--color-ink)" line={{ stroke: "var(--color-ink)", strokeWidth: 2 }} shape={() => <g />} isAnimationActive={false} />
            <Scatter name="Min-volatility candidate" data={cand("min_volatility")} fill="var(--color-chart-2)" shape="diamond" legendType="diamond" isAnimationActive={false}>
            </Scatter>
            <Scatter name="Max-Sharpe candidate" data={cand("max_sharpe")} fill="var(--color-chart-2)" shape="star" legendType="star" isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
