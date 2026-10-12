import { useId, useState } from "react";
import { Card } from "@/components/common/Card";
import type { CapmSummaryResponse } from "@/features/capm/types";
import { formatDate, formatFixed2, formatInteger, formatPercent, formatPercentPrecise } from "@/lib/formatters";

const p = (v: number) => (v < 0.001 ? "< 0.001" : v.toFixed(3));

export function EquityDetail({ data }: { data: CapmSummaryResponse }) {
  const ok = data.equities.filter((e) => e.status === "ok");
  const [id, setId] = useState(ok[0]?.asset_id ?? "");
  const selectId = useId();
  const e = ok.find((x) => x.asset_id === id);
  if (!e || !e.diagnostics) return null;
  const d = e.diagnostics;
  const groups: [string, [string, string][]][] = [
    ["Sample", [
      ["Period", `${formatDate(e.start!)} – ${formatDate(e.end!)}`],
      ["Observations", formatInteger(e.observations!)],
      ["Durbin–Watson", formatFixed2(d.durbin_watson)],
    ]],
    ["Beta", [
      ["Estimate", formatFixed2(e.beta!)],
      ["Std. error (OLS / HAC)", `${d.beta_std_error.toFixed(4)} / ${d.beta_hac_std_error.toFixed(4)}`],
      ["t-stat, p-value", `${d.beta_t_stat.toFixed(1)}, ${p(d.beta_p_value)} (HAC ${p(d.beta_hac_p_value)})`],
      ["95% CI", `${formatFixed2(d.beta_ci_low)} – ${formatFixed2(d.beta_ci_high)}`],
    ]],
    ["Regression intercept (daily units)", [
      ["Estimate per trading day", formatPercentPrecise(d.intercept_daily)],
      ["Annualized (× 252)", formatPercent(e.intercept_annualized!)],
      ["t-stat, p-value", `${d.intercept_t_stat.toFixed(2)}, ${p(d.intercept_p_value)} (HAC ${p(d.intercept_hac_p_value)}, ${d.hac_lags} lags)`],
      ["95% CI (daily)", `${formatPercentPrecise(d.intercept_ci_low)} – ${formatPercentPrecise(d.intercept_ci_high)}`],
    ]],
    ["Fit and annualized returns", [
      ["R² / adjusted R²", `${formatFixed2(e.r_squared!)} / ${formatFixed2(d.adj_r_squared)}`],
      ["Idiosyncratic volatility", formatPercent(d.residual_volatility_annualized)],
      ["Historical mean / CAPM E(R)", `${formatPercent(e.historical_mean_return!)} / ${formatPercent(e.capm_expected_return!)}`],
      ["Jensen's alpha", formatPercent(e.jensens_alpha!)],
    ]],
  ];
  return (
    <Card
      title="Equity detail"
      description="Full regression output for one equity. Jensen's alpha (historical − CAPM, annualized) equals the annualized intercept under these conventions."
      actions={
        <div className="flex w-full min-w-0 items-center gap-2 text-sm sm:w-auto">
          <label htmlFor={selectId} className="text-ink-muted">Equity</label>
          <select id={selectId} value={id} onChange={(ev) => setId(ev.target.value)} className="w-full min-w-0 rounded-md border border-border bg-surface px-2 py-1 sm:w-auto">
            {ok.map((x) => <option key={x.asset_id} value={x.asset_id}>{x.asset_id} — {x.name}</option>)}
          </select>
        </div>
      }
    >
      <div className="grid gap-6 md:grid-cols-2">
        {groups.map(([title, rows]) => (
          <section key={title}>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{title}</h3>
            <dl className="mt-2 space-y-1 text-sm">
              {rows.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-ink-muted">{k}</dt>
                  <dd className="text-right tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
    </Card>
  );
}
