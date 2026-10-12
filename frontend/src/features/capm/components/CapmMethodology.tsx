import { Card } from "@/components/common/Card";

export function CapmMethodology() {
  return (
    <Card title="Methodology" description="Single-index CAPM, estimated per equity against NIFTY 50.">
      <div className="space-y-3 text-sm">
        <p className="rounded-md bg-surface-muted px-4 py-3 font-mono text-sm">
          E(R<sub>i</sub>) = R<sub>f</sub> + β<sub>i</sub> · (E(R<sub>m</sub>) − R<sub>f</sub>)
        </p>
        <p className="text-ink-muted">
          β<sub>i</sub> is estimated by OLS regression of daily equity excess returns on daily
          market excess returns, using a risk-free rate converted to the same daily frequency.
          Jensen&apos;s alpha is the regression intercept, annualized consistently with returns.
        </p>
      </div>
    </Card>
  );
}
