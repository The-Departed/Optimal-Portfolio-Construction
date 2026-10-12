export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-2">
      <span className="sr-only">{label}</span>
      <div className="h-4 w-1/3 animate-pulse rounded bg-surface-muted" />
      <div className="h-4 w-2/3 animate-pulse rounded bg-surface-muted" />
      <div className="h-4 w-1/2 animate-pulse rounded bg-surface-muted" />
    </div>
  );
}
