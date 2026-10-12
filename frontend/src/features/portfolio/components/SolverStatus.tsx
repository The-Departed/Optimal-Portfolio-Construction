import { CheckCircle2 } from "lucide-react";
import type { OptimizationResponse } from "@/features/portfolio/types";
import { formatPercent } from "@/lib/formatters";

const sci = (v: number) => (v === 0 ? "0" : v.toExponential(1));

export function SolverStatus({ result }: { result: OptimizationResponse }) {
  const { solver, constraints } = result;
  const ok = solver.success && constraints.feasible;
  const items = [
    ["Solver", `${solver.solver}; best start “${solver.best_start}”, ${solver.iterations} iterations`],
    ["Starts", `${solver.starts_accepted} of ${solver.starts_tried} starting portfolios converged to feasible solutions`],
    ["Weights", `sum ${constraints.sum_of_weights.toFixed(12)} (raw residual ${sci(constraints.sum_residual_raw)}); range ${formatPercent(constraints.min_weight)} – ${formatPercent(constraints.max_weight)}`],
    ...(constraints.volatility_limit !== null
      ? [["Volatility limit", `${formatPercent(constraints.volatility_limit)}; slack ${sci(constraints.volatility_slack ?? 0)} (tolerance ${sci(constraints.tolerance.volatility ?? 0)})`]]
      : []),
    ...Object.entries(solver.verification).map(([k, v]) => [k.replaceAll("_", " "), sci(v)]),
  ];
  return (
    <section>
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <CheckCircle2 aria-hidden className={ok ? "size-4 text-positive" : "size-4 text-negative"} />
        {ok ? "Solver converged · all constraints satisfied" : "Solution failed validation"}
      </h3>
      <p className="mt-0.5 text-xs text-ink-muted">
        Convex problem: a converged, feasible solution is the global optimum for these estimates (within solver tolerance).
      </p>
      <dl className="mt-3 space-y-1.5 text-sm">
        {items.map(([k, v]) => (
          <div key={k} className="grid gap-1 sm:grid-cols-[9rem_1fr]">
            <dt className="text-ink-muted capitalize">{k}</dt>
            <dd className="break-words tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
