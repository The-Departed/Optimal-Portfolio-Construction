import type { CandidatePortfolio } from "@/features/portfolio/types";
import { formatFixed2, formatPercent, orDash } from "@/lib/formatters";

const TITLE = { min_volatility: "Minimum-volatility candidate", max_sharpe: "Maximum-Sharpe candidate" } as const;

export function CandidateTable({ candidate }: { candidate: CandidatePortfolio }) {
  return (
    <section className="rounded-lg border border-border p-4">
      <h3 className="text-sm font-semibold">{TITLE[candidate.label]}</h3>
      <p className="mt-0.5 text-xs text-ink-muted">Simulated portfolio #{candidate.portfolio_id} · best in sample</p>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <div><dt className="text-xs text-ink-muted">Expected return</dt><dd className="font-semibold tabular-nums">{formatPercent(candidate.expected_return)}</dd></div>
        <div><dt className="text-xs text-ink-muted">Volatility</dt><dd className="font-semibold tabular-nums">{formatPercent(candidate.volatility)}</dd></div>
        <div><dt className="text-xs text-ink-muted">Sharpe ratio</dt><dd className="font-semibold tabular-nums">{orDash(candidate.sharpe_ratio, formatFixed2)}</dd></div>
      </dl>
      <table className="mt-3 w-full text-sm tabular-nums">
        <caption className="sr-only">{TITLE[candidate.label]} weights</caption>
        <thead className="text-xs text-ink-muted">
          <tr><th scope="col" className="py-1 text-left font-medium">Asset</th><th scope="col" className="py-1 text-left font-medium">Weight</th><th scope="col" className="w-16 py-1 text-right font-medium"><span className="sr-only">Percent</span></th></tr>
        </thead>
        <tbody>
          {candidate.weights.map((w) => (
            <tr key={w.asset_id}>
              <th scope="row" className="py-1 pr-2 text-left font-normal">{w.asset_id}</th>
              <td className="w-full py-1">
                <div className="h-2 rounded-sm bg-surface-muted" aria-hidden>
                  <div className="h-2 rounded-sm bg-[var(--color-chart-1)]" style={{ width: `${Math.max(w.weight * 100, 0.5)}%` }} />
                </div>
              </td>
              <td className="py-1 pl-2 text-right">{formatPercent(w.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
