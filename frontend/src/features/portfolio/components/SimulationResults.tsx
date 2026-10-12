import { ChecksList } from "@/features/analytics/components/ChecksList";
import { CandidateTable } from "@/features/portfolio/components/CandidateTable";
import { OpportunitySetChart } from "@/features/portfolio/components/OpportunitySetChart";
import type { SimulationResponse } from "@/features/portfolio/types";
import { formatFixed2, formatInteger, formatPercent } from "@/lib/formatters";

export function SimulationResults({ data }: { data: SimulationResponse }) {
  const s = data.summary;
  const tiles = [
    { label: "Portfolios simulated", value: formatInteger(data.n_portfolios), note: `seed ${data.seed}` },
    { label: "Expected return (median)", value: formatPercent(s.expected_return.median), note: `${formatPercent(s.expected_return.min)} – ${formatPercent(s.expected_return.max)}` },
    { label: "Volatility (median)", value: formatPercent(s.volatility.median), note: `${formatPercent(s.volatility.min)} – ${formatPercent(s.volatility.max)}` },
    { label: "Sharpe ratio (median)", value: formatFixed2(s.sharpe_ratio.median), note: `${formatFixed2(s.sharpe_ratio.min)} – ${formatFixed2(s.sharpe_ratio.max)}` },
    { label: "Risk-free rate", value: formatPercent(data.inputs.risk_free_rate), note: "annualized" },
  ];
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {tiles.map((t) => (
          <div key={t.label}>
            <dt className="text-xs text-ink-muted">{t.label}</dt>
            <dd className="text-lg font-semibold tabular-nums">{t.value}</dd>
            <dd className="text-xs text-ink-muted tabular-nums">{t.note}</dd>
          </div>
        ))}
      </dl>
      <OpportunitySetChart data={data} />
      <p className="text-xs text-ink-muted">
        {data.frontier_label}: {data.frontier_criterion}. {data.scatter_selection}
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {data.candidates.map((c) => (
          <CandidateTable key={c.label} candidate={c} />
        ))}
      </div>
      <details className="rounded-lg border border-border px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium">Inputs and validation checks</summary>
        <div className="mt-3 space-y-3 text-sm">
          <p className="text-ink-muted">
            Sample {data.inputs.sample_start} – {data.inputs.sample_end} ({formatInteger(data.inputs.observations)} daily returns). {data.inputs.expected_return_convention}
          </p>
          <p className="text-ink-muted">Method: {data.method}.</p>
          <ChecksList checks={data.checks} />
          <p className="font-mono text-xs text-ink-muted">Saved: {Object.values(data.output_files).join(", ")}</p>
        </div>
      </details>
    </div>
  );
}
