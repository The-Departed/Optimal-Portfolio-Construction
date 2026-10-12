import { BarChart3, LayoutDashboard, LineChart, PieChart, TrendingUp } from "lucide-react";
import { NavLink } from "react-router";
import { cn } from "@/lib/cn";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/analytics", label: "Descriptive analytics", icon: BarChart3, end: false },
  { to: "/capm", label: "CAPM analysis", icon: LineChart, end: false },
  { to: "/portfolio", label: "Portfolio optimization", icon: PieChart, end: false },
] as const;

export function Sidebar() {
  return (
    <aside className="border-b border-border bg-surface lg:sticky lg:top-0 lg:h-dvh lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-2.5 px-5 py-4 lg:py-6">
        <span className="grid size-8 place-items-center rounded-lg bg-accent text-white dark:text-canvas">
          <TrendingUp aria-hidden className="size-4" />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-semibold">Portfolio Lab</p>
          <p className="text-xs text-ink-muted">CAPM · MPT · Monte Carlo</p>
        </div>
      </div>
      <nav aria-label="Primary" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:pb-0">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-accent-soft font-medium text-accent"
                  : "text-ink-muted hover:bg-surface-muted hover:text-ink",
              )
            }
          >
            <Icon aria-hidden className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
