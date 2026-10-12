import { AlertTriangle } from "lucide-react";
import { ApiError } from "@/lib/api-client";

export function ErrorAlert({ error, title = "Something went wrong" }: { error: unknown; title?: string }) {
  const message = error instanceof Error ? error.message : "An unexpected error occurred.";
  const code = error instanceof ApiError ? error.code : null;
  return (
    <div role="alert" className="flex gap-3 rounded-lg border border-negative/30 bg-negative-soft p-4 text-sm">
      <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-negative" />
      <div>
        <p className="font-medium text-negative">{title}</p>
        <p className="mt-1 text-ink">{message}</p>
        {code && <p className="mt-1 font-mono text-xs text-ink-muted">{code}</p>}
      </div>
    </div>
  );
}
