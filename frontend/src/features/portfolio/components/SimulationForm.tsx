import { Dices } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import type { SimulationRequest } from "@/features/portfolio/types";

export const DEFAULT_SIMULATIONS = 50_000;
export const DEFAULT_SEED = 42;
const MIN_N = 100;
const MAX_N = 200_000;

function validate(n: string, seed: string): { request: SimulationRequest } | { errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  const nv = Number(n);
  const sv = Number(seed);
  if (!Number.isInteger(nv) || nv < MIN_N || nv > MAX_N) errors.n = `Enter a whole number from ${MIN_N.toLocaleString("en-IN")} to ${MAX_N.toLocaleString("en-IN")}.`;
  if (!Number.isInteger(sv) || sv < 0 || sv > 4294967295) errors.seed = "Enter a whole number from 0 to 4,294,967,295.";
  return Object.keys(errors).length ? { errors } : { request: { n_portfolios: nv, seed: sv } };
}

interface SimulationFormProps {
  disabled: boolean;
  pending: boolean;
  onRun: (request: SimulationRequest) => void;
}

export function SimulationForm({ disabled, pending, onRun }: SimulationFormProps) {
  const [n, setN] = useState(String(DEFAULT_SIMULATIONS));
  const [seed, setSeed] = useState(String(DEFAULT_SEED));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const nId = useId();
  const seedId = useId();

  function submit(event: FormEvent) {
    event.preventDefault();
    const result = validate(n, seed);
    if ("errors" in result) return setErrors(result.errors);
    setErrors({});
    onRun(result.request);
  }

  const field = "mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm tabular-nums outline-none focus:border-accent";
  return (
    <form onSubmit={submit} noValidate className="flex flex-wrap items-end gap-4">
      <div className="w-48">
        <label htmlFor={nId} className="block text-sm font-medium">Number of portfolios</label>
        <input id={nId} type="number" inputMode="numeric" value={n} onChange={(e) => setN(e.target.value)} min={MIN_N} max={MAX_N} step={1000}
          aria-invalid={Boolean(errors.n)} aria-describedby={errors.n ? `${nId}-err` : undefined} className={field} />
        {errors.n && <p id={`${nId}-err`} className="mt-1 text-xs text-negative">{errors.n}</p>}
      </div>
      <div className="w-40">
        <label htmlFor={seedId} className="block text-sm font-medium">Random seed</label>
        <input id={seedId} type="number" inputMode="numeric" value={seed} onChange={(e) => setSeed(e.target.value)} min={0} step={1}
          aria-invalid={Boolean(errors.seed)} aria-describedby={errors.seed ? `${seedId}-err` : undefined} className={field} />
        {errors.seed && <p id={`${seedId}-err`} className="mt-1 text-xs text-negative">{errors.seed}</p>}
      </div>
      <button type="submit" disabled={disabled || pending}
        className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 dark:text-canvas">
        <Dices aria-hidden className="size-4" />
        {pending ? "Simulating…" : "Run simulation"}
      </button>
      <p className="basis-full text-xs text-ink-muted">
        Defaults: {DEFAULT_SIMULATIONS.toLocaleString("en-IN")} portfolios, seed {DEFAULT_SEED}. The same seed and count reproduce identical results.
      </p>
    </form>
  );
}
