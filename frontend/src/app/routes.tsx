import type { RouteObject } from "react-router";
import { AppLayout } from "@/components/layout/AppLayout";
import { NotFoundPage } from "@/components/layout/NotFoundPage";
import { DashboardPage } from "@/features/dashboard/page";

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
      { path: "capm", lazy: () => import("@/features/capm/page").then((m) => ({ Component: m.CapmPage })) },
      {
        path: "portfolio",
        lazy: () => import("@/features/portfolio/page").then((m) => ({ Component: m.PortfolioPage })),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
