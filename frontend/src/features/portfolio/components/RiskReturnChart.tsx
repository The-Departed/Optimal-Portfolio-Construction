import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { LoadingState } from "@/components/common/LoadingState";
import { useComparisonSimulation, useFrontier } from "@/features/portfolio/hooks/usePortfolioQueries";
import type { InvestorProfile, OptimizationResponse } from "@/features/portfolio/types";
import { formatFixed2, formatPercent, formatPercentTick } from "@/lib/formatters";

type Point = { vol: number; ret: number; sharpe: number | null; name: string };

const SHAPE: Record<InvestorProfile, "triangle" | "star" | "square"> = { conservative: "triangle", balanced: "star", growth: "square" };

function PointTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  const p = active ? payload?.[0]?.payload : undefined;
  if (!p) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-sm">
      <p className="font-medium">{p.name}</p>
      <p>Expected return {formatPercent(p.ret)}</p>
      <p>Volatility {formatPercent(p.vol)}</p>
      <p>Sharpe {p.sharpe === null ? "—" : formatFixed2(p.sharpe)}</p>
    </div>
  );
}

interface RiskReturnChartProps {
  results: Partial<Record<InvestorProfile, OptimizationResponse>>;
  selected: InvestorProfile;
}

export function RiskReturnChart({ results, selected }: RiskReturnChartProps) {
  const current = results[selected];
  const n = current?.comparison.n_portfolios ?? 50000;
  const seed = current?.comparison.seed ?? 42;
  const sim = useComparisonSimulation(n, seed, Boolean(current));
  const frontier = useFrontier(Boolean(current));
  if (!current) return null;
  if (sim.isPending || frontier.isPending) return <LoadingState label="Loading opportunity set…" />;

  const sampled: Point[] = sim.data
    ? sim.data.scatter.portfolio_ids.map((_, i) => ({
        vol: sim.data.scatter.volatilities[i]!,
        ret: sim.data.scatter.expected_returns[i]!,
        sharpe: sim.data.scatter.sharpe_ratios[i] ?? null,
        name: "Simulated portfolio",
      }))
    : [];
  const exact: Point[] = (frontier.data?.points ?? []).map((p) => ({ vol: p.volatility, ret: p.expected_return, sharpe: p.sharpe_ratio, name: "Efficient frontier (optimizer)" }));
  const cand = current.comparison.candidate;
  const candidate: Point[] = cand ? [{ vol: cand.volatility, ret: cand.expected_return, sharpe: cand.sharpe_ratio, name: `Monte Carlo candidate #${cand.portfolio_id}` }] : [];
  const optimized = (Object.values(results) as OptimizationResponse[]).map((r) => ({
    profile: r.profile,
    point: { vol: r.portfolio.volatility, ret: r.portfolio.expected_return, sharpe: r.portfolio.sharpe_ratio, name: `${r.label} (optimized)` },
  }));

  return (
    <figure>
      <figcaption className="mb-1 text-sm font-medium">Optimized portfolios on the risk-return plane</figcaption>
      <p className="mb-2 text-xs text-ink-muted">
        Annualized estimates. Grey-blue dots: {sampled.length.toLocaleString("en-IN")} of {n.toLocaleString("en-IN")} simulated portfolios (seed {seed}); line: exact long-only frontier from the optimizer.
      </p>
      <div className="h-[26rem]" role="img" aria-label="Risk-return chart with optimized portfolios">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ left: 4, right: 16, top: 8, bottom: 16 }}>
            <CartesianGrid stroke="var(--color-grid)" />
            <XAxis type="number" dataKey="vol" domain={[0, "auto"]} tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} tickLine={false}
              label={{ value: "Annualized volatility", position: "insideBottom", offset: -10, fontSize: 11, fill: "var(--color-ink-muted)" }} />
            <YAxis type="number" dataKey="ret" domain={["auto", "auto"]} tickFormatter={(v: number) => formatPercentTick(v)} tick={{ fontSize: 11, fill: "var(--color-ink-muted)" }} axisLine={false} tickLine={false} width={48}
              label={{ value: "Expected return (annualized)", angle: -90, position: "insideLeft", offset: 10, fontSize: 11, fill: "var(--color-ink-muted)" }} />
            <ZAxis range={[14, 14]} />
            <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3" }} />
            <Legend verticalAlign="top" wrapperStyle={{ fontSize: 12, paddingBottom: 8 }} formatter={(value) => <span style={{ color: "var(--color-ink-muted)" }}>{value}</span>} />
            <Scatter name="Simulated portfolios" data={sampled} fill="var(--color-chart-1)" fillOpacity={0.25} isAnimationActive={false} />
            <Scatter name="Efficient frontier (optimizer)" data={exact} fill="var(--color-ink)" line={{ stroke: "var(--color-ink)", strokeWidth: 2 }} shape={() => <g />} isAnimationActive={false} />
            <Scatter name="Monte Carlo candidate" data={candidate} fill="var(--color-ink-muted)" shape="diamond" legendType="diamond" isAnimationActive={false} />
            {optimized.map(({ profile, point }) => (
              <Scatter
                key={profile}
                name={point.name}
                data={[point]}
                fill="var(--color-chart-2)"
                shape={SHAPE[profile]}
                legendType={SHAPE[profile]}
                isAnimationActive={false}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
