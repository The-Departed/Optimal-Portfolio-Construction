import { useId } from "react";

interface MaxVolatilityInputProps {
  value: string;
  onChange: (value: string) => void;
  error: string | null;
}

export function MaxVolatilityInput({ value, onChange, error }: MaxVolatilityInputProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  return (
    <div className="max-w-xs">
      <label htmlFor={id} className="block text-sm font-medium">
        Maximum annualized volatility (σ<sub>max</sub>)
      </label>
      <div className="mt-1.5 flex items-center rounded-md border border-border bg-surface focus-within:border-accent">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          min={0}
          step={0.5}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error !== null}
          aria-describedby={error ? `${hintId} ${errorId}` : hintId}
          className="w-full bg-transparent px-3 py-2 text-sm outline-none"
          placeholder="e.g. 15"
        />
        <span className="pr-3 text-sm text-ink-muted">%</span>
      </div>
      <p id={hintId} className="mt-1 text-xs text-ink-muted">
        A hard constraint. If no long-only portfolio satisfies it, the optimizer reports it as infeasible.
      </p>
      {error && (
        <p id={errorId} className="mt-1 text-xs text-negative">
          {error}
        </p>
      )}
    </div>
  );
}
