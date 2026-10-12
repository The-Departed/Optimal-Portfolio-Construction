import { cn } from "@/lib/cn";
import type { Tone } from "@/features/dashboard/status";

const TONE: Record<Tone, string> = {
  neutral: "border-border",
  positive: "border-border",
  warning: "border-warning/40 bg-warning-soft",
  negative: "border-negative/40 bg-negative-soft",
};

interface IssueListProps {
  title: string;
  tone: Tone;
  items: string[];
  open?: boolean;
}

/** Collapsible list of validation messages; renders nothing when empty. */
export function IssueList({ title, tone, items, open = false }: IssueListProps) {
  if (items.length === 0) return null;
  return (
    <details open={open} className={cn("rounded-lg border px-4 py-3 text-sm", TONE[tone])}>
      <summary className="cursor-pointer font-medium">
        {title} ({items.length})
      </summary>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-muted">
        {items.map((item) => (
          <li key={item} className="break-words">
            {item}
          </li>
        ))}
      </ul>
    </details>
  );
}
