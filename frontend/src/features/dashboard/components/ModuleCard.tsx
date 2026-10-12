import { ArrowRight, type LucideIcon } from "lucide-react";
import { Link } from "react-router";

interface ModuleCardProps {
  to: string;
  icon: LucideIcon;
  title: string;
  description: string;
}

export function ModuleCard({ to, icon: Icon, title, description }: ModuleCardProps) {
  return (
    <Link
      to={to}
      className="group flex flex-col rounded-xl border border-border bg-surface p-5 shadow-sm transition-colors hover:border-accent"
    >
      <Icon aria-hidden className="size-5 text-accent" />
      <h2 className="mt-3 text-sm font-semibold">{title}</h2>
      <p className="mt-1 flex-1 text-sm text-ink-muted">{description}</p>
      <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent">
        Open module
        <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
