import { StatusBadge } from "@/components/common/StatusBadge";
import { AllocationChart } from "@/features/portfolio/components/AllocationChart";
import { ComparisonTable } from "@/features/portfolio/components/ComparisonTable";
import { SolverStatus } from "@/features/portfolio/components/SolverStatus";
import type { OptimizationResponse } from "@/features/portfolio/types";
import { formatFixed2, formatInteger, formatPercent, orDash } from "@/lib/formatters";

export function OptimizationResult({ result }: { result: OptimizationResponse }) {
  const p = result.portfolio;
  const valid = result.status === "optimal" && result.solver.success && result.constraints.feasible;
  const tiles = [
    { label: "Expected return (annualized)", value: formatPercent(p.expected_return) },
    { label: "Volatility (annualized)", value: formatPercent(p.volatility) },
    { label: "Sharpe ratio", value: orDash(p.sharpe_ratio, formatFixed2) },
    ...(result.max_volatility !== null ? [{ label: "Volatility limit", value: formatPercent(result.max_volatility) }] : []),
  ];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-semibold">{result.label} portfolio</h3>
        <StatusBadge tone={valid ? "positive" : "negative"}>{valid ? "Optimal for these estimates" : "Not valid"}</StatusBadge>
      </div>
      <p className="-mt-4 text-sm text-ink-muted">{result.objective}</p>
      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((t) => (
          <div key={t.label}>
            <dt className="text-xs text-ink-muted">{t.label}</dt>
            <dd className="text-xl font-semibold tabular-nums">{t.value}</dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-6 lg:grid-cols-2">
        <AllocationChart weights={p.weights} title="Asset allocation" />
        <table className="self-start text-sm tabular-nums">
          <caption className="mb-2 text-left text-sm font-medium">Asset weights</caption>
          <thead className="border-b border-border text-xs text-ink-muted">
            <tr><th scope="col" className="py-1.5 text-left font-medium">Asset</th><th scope="col" className="py-1.5 text-right font-medium">Weight</th><th scope="col" className="py-1.5 text-right font-medium">Expected return input</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {p.weights.map((w) => (
              <tr key={w.asset_id}>
                <th scope="row" className="py-1.5 pr-6 text-left font-normal">{w.asset_id}</th>
                <td className="py-1.5 text-right font-medium">{formatPercent(w.weight)}</td>
                <td className="py-1.5 pl-6 text-right text-ink-muted">{formatPercent(result.inputs.expected_returns[w.asset_id] ?? NaN)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <SolverStatus result={result} />
        <ComparisonTable result={result} />
      </div>
      <details className="rounded-lg border border-border px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium">Data and estimation methodology</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-muted">
          <li>Sample {result.inputs.sample_start} – {result.inputs.sample_end} ({formatInteger(result.inputs.observations)} daily returns); dataset generated {result.inputs.dataset_generated_at}.</li>
          <li>Expected returns: {result.inputs.expected_return_convention}</li>
          <li>Covariance: {result.inputs.covariance_convention}</li>
          <li>Risk-free rate {formatPercent(result.inputs.risk_free_rate)}: {result.inputs.risk_free_convention}</li>
          <li>Formulation: <span className="font-mono text-xs">{result.formulation}</span></li>
        </ul>
      </details>
    </div>
  );
}
