import { Card } from "@/components/common/Card";
import type { CapmSummaryResponse } from "@/features/capm/types";
import { formatFixed2, formatInteger, formatPercent, orDash } from "@/lib/formatters";

const p = (v: number) => (v < 0.001 ? "<0.001" : v.toFixed(3));

export function CapmTable({ data }: { data: CapmSummaryResponse }) {
  return (
    <Card
      title="CAPM results"
      description="Annualized decimals shown as percent. Alpha = historical mean − CAPM expected return; p-values from OLS (HAC in brackets)."
    >
      <div className="-mx-5 overflow-x-auto">
        <table className="w-full min-w-[60rem] text-right text-sm tabular-nums">
          <caption className="sr-only">CAPM estimates for six equities</caption>
          <thead className="border-y border-border bg-surface-muted text-xs text-ink-muted">
            <tr>
              <th scope="col" className="px-5 py-2 text-left font-medium">Equity</th>
              <th scope="col" className="px-3 py-2 font-medium">Obs.</th>
              <th scope="col" className="px-3 py-2 font-medium">Hist. mean</th>
              <th scope="col" className="px-3 py-2 font-medium">CAGR</th>
              <th scope="col" className="px-3 py-2 font-medium">Volatility</th>
              <th scope="col" className="px-3 py-2 font-medium">Beta [95% CI]</th>
              <th scope="col" className="px-3 py-2 font-medium">CAPM E(R)</th>
              <th scope="col" className="px-3 py-2 font-medium">Jensen&apos;s alpha</th>
              <th scope="col" className="px-3 py-2 font-medium">Alpha p</th>
              <th scope="col" className="px-5 py-2 font-medium">R²</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.equities.map((e) =>
              e.status !== "ok" ? (
                <tr key={e.asset_id}>
                  <th scope="row" className="px-5 py-2.5 text-left font-medium">{e.asset_id}</th>
                  <td colSpan={9} className="px-5 py-2.5 text-left text-negative">Regression failed: {e.error}</td>
                </tr>
              ) : (
                <tr key={e.asset_id}>
                  <th scope="row" className="px-5 py-2.5 text-left font-normal">
                    <span className="font-medium">{e.asset_id}</span>
                    <span className="block text-xs text-ink-muted">{e.sector}</span>
                  </th>
                  <td className="px-3 py-2.5">{orDash(e.observations, formatInteger)}</td>
                  <td className="px-3 py-2.5">{orDash(e.historical_mean_return, formatPercent)}</td>
                  <td className="px-3 py-2.5 text-ink-muted">{orDash(e.historical_cagr, formatPercent)}</td>
                  <td className="px-3 py-2.5">{orDash(e.annualized_volatility, formatPercent)}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {orDash(e.beta, formatFixed2)}
                    {e.diagnostics && (
                      <span className="block text-xs text-ink-muted">
                        [{formatFixed2(e.diagnostics.beta_ci_low)}, {formatFixed2(e.diagnostics.beta_ci_high)}]
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5">{orDash(e.capm_expected_return, formatPercent)}</td>
                  <td className="px-3 py-2.5 font-medium">{orDash(e.jensens_alpha, formatPercent)}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {e.diagnostics ? `${p(e.diagnostics.intercept_p_value)} (${p(e.diagnostics.intercept_hac_p_value)})` : "—"}
                  </td>
                  <td className="px-5 py-2.5">{orDash(e.r_squared, formatFixed2)}</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-ink-muted">{data.disclaimer}</p>
    </Card>
  );
}
