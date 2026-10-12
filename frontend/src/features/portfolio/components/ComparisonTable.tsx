import type { OptimizationResponse } from "@/features/portfolio/types";
import { formatFixed2, formatInteger, formatPercent, orDash } from "@/lib/formatters";

const signed = (fmt: (v: number) => string) => (v: number) => (v > 0 ? "+" : "") + fmt(v);

export function ComparisonTable({ result }: { result: OptimizationResponse }) {
  const c = result.comparison;
  const p = result.portfolio;
  const cand = c.candidate;
  const rows = [
    { label: "Expected return", opt: formatPercent(p.expected_return), mc: cand ? formatPercent(cand.expected_return) : "—", diff: orDash(c.return_difference, signed(formatPercent)) },
    { label: "Volatility", opt: formatPercent(p.volatility), mc: cand ? formatPercent(cand.volatility) : "—", diff: orDash(c.volatility_difference, signed(formatPercent)) },
    { label: "Sharpe ratio", opt: orDash(p.sharpe_ratio, formatFixed2), mc: cand ? orDash(cand.sharpe_ratio, formatFixed2) : "—", diff: orDash(c.sharpe_difference, signed(formatFixed2)) },
  ];
  return (
    <section>
      <h3 className="text-sm font-semibold">Monte Carlo vs constrained optimizer</h3>
      <p className="mt-0.5 text-xs text-ink-muted">
        Candidate: {c.candidate_rule} from {formatInteger(c.n_portfolios)} simulated portfolios (seed {c.seed}
        {cand ? `, portfolio #${cand.portfolio_id}` : ""}). {c.note}
      </p>
      <table className="mt-3 w-full text-right text-sm tabular-nums">
        <caption className="sr-only">Optimizer compared with the Monte Carlo candidate</caption>
        <thead className="border-b border-border text-xs text-ink-muted">
          <tr>
            <th scope="col" className="py-2 text-left font-medium">Metric</th>
            <th scope="col" className="py-2 font-medium">Optimizer</th>
            <th scope="col" className="py-2 font-medium">Simulated candidate</th>
            <th scope="col" className="py-2 font-medium">Difference</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((r) => (
            <tr key={r.label}>
              <th scope="row" className="py-2 text-left font-normal">{r.label}</th>
              <td className="py-2 font-medium">{r.opt}</td>
              <td className="py-2">{r.mc}</td>
              <td className="py-2">{r.diff}</td>
            </tr>
          ))}
          <tr>
            <th scope="row" className="py-2 text-left font-normal">Satisfies constraints</th>
            <td className="py-2">{c.optimizer_passes_checks ? "Yes" : "No"}</td>
            <td className="py-2">{c.candidate_satisfies_constraints === null ? "—" : c.candidate_satisfies_constraints ? "Yes" : "No"}</td>
            <td />
          </tr>
        </tbody>
      </table>
    </section>
  );
}
