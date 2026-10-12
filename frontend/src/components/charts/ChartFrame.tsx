import { ChartNoAxesCombined } from "lucide-react";
import type { ReactNode } from "react";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";

interface ChartFrameProps {
  title: string;
  description: string;
  /** Chart content. When omitted, an empty state is shown instead of placeholder data. */
  children?: ReactNode;
  emptyMessage?: string;
}

export function ChartFrame({ title, description, children, emptyMessage }: ChartFrameProps) {
  return (
    <Card title={title} description={description}>
      {children ?? (
        <EmptyState
          icon={ChartNoAxesCombined}
          title="No data to plot"
          description={emptyMessage ?? "This chart renders backend results once they are available."}
        />
      )}
    </Card>
  );
}
