import { DatabaseZap } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingState } from "@/components/common/LoadingState";
import { useDataStatus } from "@/hooks/useDataStatus";

/** Renders children only when the backend reports a validated dataset. */
export function RequireData({ children }: { children: ReactNode }) {
  const { data, isPending, error } = useDataStatus();
  if (isPending) return <LoadingState label="Checking dataset status…" />;
  if (error) return <ErrorAlert title="Could not check dataset status" error={error} />;
  if (!data.ready) {
    return (
      <EmptyState
        icon={DatabaseZap}
        title="Analysis not available yet"
        description={`${data.message} Results will appear here once a validated dataset exists.`}
      >
        <Link to="/" className="text-sm font-medium text-accent hover:underline">
          View dataset status
        </Link>
      </EmptyState>
    );
  }
  return <>{children}</>;
}
