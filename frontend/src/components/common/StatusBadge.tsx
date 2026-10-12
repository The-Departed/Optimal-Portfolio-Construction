import { cn } from "@/lib/cn";

type Tone = "neutral" | "positive" | "warning" | "negative";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-muted text-ink-muted",
  positive: "bg-accent-soft text-positive",
  warning: "bg-warning-soft text-warning",
  negative: "bg-negative-soft text-negative",
};

export function StatusBadge({ tone, children }: { tone: Tone; children: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
      )}
    >
      <span aria-hidden className="size-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}
