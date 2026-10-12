import { Play } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { MaxVolatilityInput } from "@/features/portfolio/components/MaxVolatilityInput";
import { ProfileSelector } from "@/features/portfolio/components/ProfileSelector";
import { useProfiles } from "@/features/portfolio/hooks/useProfiles";
import type { InvestorProfile, OptimizationRequest } from "@/features/portfolio/types";

/** Validates the sigma_max field (entered in percent) and returns a decimal, or an error. */
export function parseMaxVolatility(raw: string): { value: number } | { error: string } {
  if (raw.trim() === "") return { error: "Enter a maximum volatility for the growth profile." };
  const pct = Number(raw);
  if (!Number.isFinite(pct) || pct <= 0) return { error: "Must be a number greater than 0%." };
  if (pct >= 500) return { error: "Must be below 500%." };
  return { value: pct / 100 };
}

interface OptimizationFormProps {
  dataReady: boolean;
  pending: boolean;
  profile: InvestorProfile;
  onProfileChange: (profile: InvestorProfile) => void;
  onSubmit: (request: OptimizationRequest) => void;
}

export function OptimizationForm({ dataReady, pending, profile, onProfileChange, onSubmit }: OptimizationFormProps) {
  const profiles = useProfiles();
  const [maxVol, setMaxVol] = useState("");
  const [touched, setTouched] = useState(false);

  const definition = profiles.data?.find((p) => p.profile === profile);
  const needsMaxVol = definition?.requires_max_volatility ?? false;
  const parsed = needsMaxVol ? parseMaxVolatility(maxVol) : null;
  const fieldError = touched && parsed && "error" in parsed ? parsed.error : null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (pending || (parsed && "error" in parsed)) return;
    onSubmit(parsed ? { profile, max_volatility: parsed.value } : { profile });
  }

  if (profiles.isPending) return <LoadingState label="Loading investor profiles…" />;
  if (profiles.error) return <ErrorAlert title="Could not load investor profiles" error={profiles.error} />;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <ProfileSelector profiles={profiles.data} value={profile} onChange={onProfileChange} />
      {definition && (
        <div className="rounded-md bg-surface-muted px-4 py-3 text-sm">
          <p className="font-medium">Objective &amp; constraints</p>
          <p className="mt-1 font-mono text-xs leading-relaxed text-ink-muted">{definition.formulation}</p>
          <p className="mt-1 text-xs text-ink-muted">No short selling or leverage: every weight between 0% and 100%, weights sum to 100%.</p>
        </div>
      )}
      {needsMaxVol && <MaxVolatilityInput value={maxVol} onChange={setMaxVol} error={fieldError} />}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={!dataReady || pending}
          className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 dark:text-canvas"
        >
          <Play aria-hidden className="size-4" />
          {pending ? "Optimizing…" : "Run optimization"}
        </button>
        {!dataReady && <p className="text-sm text-ink-muted">Available once a validated dataset exists.</p>}
      </div>
    </form>
  );
}
