import { Play } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { MaxVolatilityInput } from "@/features/portfolio/components/MaxVolatilityInput";
import { ProfileSelector } from "@/features/portfolio/components/ProfileSelector";
import { useOptimizePortfolio } from "@/features/portfolio/hooks/useOptimizePortfolio";
import { useProfiles } from "@/features/portfolio/hooks/useProfiles";
import type { InvestorProfile, OptimizationRequest } from "@/features/portfolio/types";

/** Validates the sigma_max field (entered in percent) and returns a decimal, or an error. */
function parseMaxVolatility(raw: string): { value: number } | { error: string } {
  if (raw.trim() === "") return { error: "Enter a maximum volatility for the growth profile." };
  const pct = Number(raw);
  if (!Number.isFinite(pct) || pct <= 0) return { error: "Must be a number greater than 0%." };
  if (pct >= 500) return { error: "Must be below 500%." };
  return { value: pct / 100 };
}

export function OptimizationForm({ dataReady }: { dataReady: boolean }) {
  const profiles = useProfiles();
  const optimize = useOptimizePortfolio();
  const [profile, setProfile] = useState<InvestorProfile>("balanced");
  const [maxVol, setMaxVol] = useState("");
  const [touched, setTouched] = useState(false);

  const definition = profiles.data?.find((p) => p.profile === profile);
  const needsMaxVol = definition?.requires_max_volatility ?? false;
  const parsed = needsMaxVol ? parseMaxVolatility(maxVol) : null;
  const fieldError = touched && parsed && "error" in parsed ? parsed.error : null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (parsed && "error" in parsed) return;
    const request: OptimizationRequest = parsed ? { profile, max_volatility: parsed.value } : { profile };
    optimize.mutate(request);
  }

  if (profiles.isPending) return <LoadingState label="Loading investor profiles…" />;
  if (profiles.error) return <ErrorAlert title="Could not load investor profiles" error={profiles.error} />;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <ProfileSelector
        profiles={profiles.data}
        value={profile}
        onChange={(p) => {
          setProfile(p);
          optimize.reset();
        }}
      />
      {definition && (
        <div className="rounded-md bg-surface-muted px-4 py-3 text-sm">
          <p className="font-medium">Objective &amp; constraints</p>
          <p className="mt-1 font-mono text-xs leading-relaxed text-ink-muted">{definition.formulation}</p>
        </div>
      )}
      {needsMaxVol && <MaxVolatilityInput value={maxVol} onChange={setMaxVol} error={fieldError} />}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={!dataReady || optimize.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 dark:text-canvas"
        >
          <Play aria-hidden className="size-4" />
          {optimize.isPending ? "Optimizing…" : "Run optimization"}
        </button>
        {!dataReady && (
          <p className="text-sm text-ink-muted">Available once a validated dataset exists.</p>
        )}
      </div>
      {optimize.error && <ErrorAlert title="Optimization did not complete" error={optimize.error} />}
    </form>
  );
}
