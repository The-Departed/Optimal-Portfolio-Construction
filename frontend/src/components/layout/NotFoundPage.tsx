import { Compass } from "lucide-react";
import { Link } from "react-router";
import { EmptyState } from "@/components/common/EmptyState";

export function NotFoundPage() {
  return (
    <EmptyState icon={Compass} title="Page not found" description="This page does not exist.">
      <Link to="/" className="text-sm font-medium text-accent hover:underline">
        Back to dashboard
      </Link>
    </EmptyState>
  );
}
