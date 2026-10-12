import { RadioGroup } from "radix-ui";
import { cn } from "@/lib/cn";
import type { InvestorProfile, ProfileDefinition } from "@/features/portfolio/types";

interface ProfileSelectorProps {
  profiles: ProfileDefinition[];
  value: InvestorProfile;
  onChange: (profile: InvestorProfile) => void;
}

export function ProfileSelector({ profiles, value, onChange }: ProfileSelectorProps) {
  return (
    <RadioGroup.Root
      aria-label="Investor profile"
      value={value}
      onValueChange={(v) => onChange(v as InvestorProfile)}
      className="grid gap-3 md:grid-cols-3"
    >
      {profiles.map((p) => (
        <RadioGroup.Item
          key={p.profile}
          value={p.profile}
          className={cn(
            "rounded-lg border p-4 text-left transition-colors",
            "data-[state=checked]:border-accent data-[state=checked]:bg-accent-soft",
            "data-[state=unchecked]:border-border data-[state=unchecked]:hover:bg-surface-muted",
          )}
        >
          <span className="block text-sm font-semibold">{p.label}</span>
          <span className="mt-1 block text-sm text-ink-muted">{p.objective}</span>
        </RadioGroup.Item>
      ))}
    </RadioGroup.Root>
  );
}
