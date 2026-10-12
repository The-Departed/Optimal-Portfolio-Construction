import { Card } from "@/components/common/Card";
import type { CapmSummaryResponse } from "@/features/capm/types";
import { formatDate, formatInteger, formatPercent } from "@/lib/formatters";

export function CapmOverview({ data }: { data: CapmSummaryResponse }) {
  const items = [
    { label: "Regression sample", value: `${formatDate(data.sample_start)} – ${formatDate(data.sample_end)}` },
    { label: "Daily observations", value: formatInteger(data.observations) },
    { label: "R_f (annualized)", value: formatPercent(data.risk_free.annualized_rate) },
    { label: "E(R_m) NIFTY 50", value: formatPercent(data.market.mean_return) },
    { label: "Market risk premium", value: formatPercent(data.market.market_risk_premium) },
  ];
  return (
    <Card title="Market inputs" description="Common to all six regressions.">
      <dl className="grid grid-cols-2 gap-4 text-sm lg:grid-cols-5">
        {items.map((i) => (
          <div key={i.label}>
            <dt className="text-ink-muted">{i.label}</dt>
            <dd className="text-base font-semibold tabular-nums">{i.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-ink-muted">
        R_f: {data.risk_free.convention} Average quoted yield applied: {formatPercent(data.risk_free.mean_quoted_yield)}.
      </p>
    </Card>
  );
}
