import type { RouteObject } from "react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { NotFoundPage } from "@/components/layout/NotFoundPage";
import { CapmPage } from "@/features/capm/page";
import { DashboardPage } from "@/features/dashboard/page";
import { PortfolioPage } from "@/features/portfolio/page";

export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      {
        path: "analytics",
        // Charts (Recharts) load only when this page is opened.
        lazy: () => import("@/features/analytics/page").then((m) => ({ Component: m.AnalyticsPage })),
      },
      { path: "capm", element: <CapmPage /> },
      { path: "portfolio", element: <PortfolioPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
