import { Card } from "@/components/common/Card";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { SimulationForm } from "@/features/portfolio/components/SimulationForm";
import { SimulationResults } from "@/features/portfolio/components/SimulationResults";
import { useSimulation } from "@/features/portfolio/hooks/useSimulation";

export function MonteCarloPanel({ dataReady }: { dataReady: boolean }) {
  const sim = useSimulation();
  return (
    <Card
      title="Monte Carlo opportunity set"
      description="Random long-only allocations across all eight assets (0 ≤ wᵢ ≤ 1, Σw = 1). Expected returns are historical arithmetic means; covariance is the annualized sample estimate."
    >
      <SimulationForm disabled={!dataReady} pending={sim.isPending} onRun={(r) => sim.mutate(r)} />
      <div className="mt-6">
        {sim.isPending && <LoadingState label="Running simulation…" />}
        {sim.error && <ErrorAlert title="Simulation failed" error={sim.error} />}
        {sim.data && <SimulationResults data={sim.data} />}
        {!sim.data && !sim.isPending && !sim.error && (
          <p className="text-sm text-ink-muted">{dataReady ? "Run a simulation to explore the opportunity set." : "Available once a validated dataset exists."}</p>
        )}
      </div>
    </Card>
  );
}
