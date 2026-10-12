import { CheckCircle2, CircleAlert, XCircle } from "lucide-react";
import type { AnalyticsCheck } from "@/features/analytics/types";

const ICON = {
  pass: { Icon: CheckCircle2, cls: "text-positive", label: "Passed" },
  warn: { Icon: CircleAlert, cls: "text-warning", label: "Warning" },
  fail: { Icon: XCircle, cls: "text-negative", label: "Failed" },
} as const;

export function ChecksList({ checks }: { checks: AnalyticsCheck[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {checks.filter((c) => c.status !== "warn").map((c) => {
        const { Icon, cls, label } = ICON[c.status];
        return (
          <li key={c.name} className="flex gap-2">
            <Icon aria-label={label} className={`mt-0.5 size-4 shrink-0 ${cls}`} />
            <span>
              <span className="font-mono text-xs">{c.name}</span>
              <span className="text-ink-muted"> — {c.detail}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
