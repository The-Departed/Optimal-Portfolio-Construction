import { Card } from "@/components/common/Card";

export function CapmMethodology() {
  return (
    <Card title="Methodology" description="Single-index CAPM, estimated per equity against NIFTY 50.">
      <div className="space-y-3 text-sm">
        <p className="rounded-md bg-surface-muted px-4 py-3 font-mono text-sm">
          R<sub>i,t</sub> − R<sub>f,t</sub> = a<sub>i</sub> + β<sub>i</sub> (R<sub>m,t</sub> − R<sub>f,t</sub>) + ε<sub>i,t</sub>
          <span className="mx-3 text-ink-muted">·</span>
          E(R<sub>i</sub>) = R<sub>f</sub> + β<sub>i</sub> (E(R<sub>m</sub>) − R<sub>f</sub>)
        </p>
        <ul className="list-disc space-y-1 pl-5 text-ink-muted">
          <li>OLS on daily excess returns of the common sample; R<sub>f,t</sub> accrues the latest 91-day T-bill auction yield over each interval&apos;s calendar days.</li>
          <li>Annualized returns use the arithmetic convention (mean daily return × 252), the same as R<sub>f</sub> and E(R<sub>m</sub>).</li>
          <li>
            <strong className="font-medium text-ink">Jensen&apos;s alpha</strong> = historical annualized mean return − CAPM expected return. With these
            conventions it equals the regression intercept × 252 exactly.
          </li>
        </ul>
      </div>
    </Card>
  );
}
