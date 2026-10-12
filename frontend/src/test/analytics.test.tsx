import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { analyticsSummary, correlation, distribution, riskFree, statistics } from "@/test/analyticsFixtures";
import { dataMissing, dataReady, universe } from "@/test/fixtures";
import { mockApi, renderRoute } from "@/test/render";

const ok = (body: unknown) => () => ({ status: 200, body });

const handlers = {
  "/data/status": ok(dataReady),
  "/assets": ok(universe),
  "/analytics/summary": ok(analyticsSummary),
  "/analytics/statistics?sample=common": ok(statistics),
  "/analytics/statistics?sample=individual": ok({ ...statistics, sample: "individual" }),
  "/analytics/correlation": ok(correlation),
  "/analytics/distribution?series=AAA&sample=common&bins=50": ok(distribution),
  "/analytics/risk-free": ok(riskFree),
};

describe("descriptive analytics page", () => {
  it("renders backend statistics with units and unavailable values as dashes", async () => {
    mockApi(handlers);
    renderRoute("/analytics");
    const table = await screen.findByRole("table", { name: /descriptive statistics of daily returns/i });
    const row = within(table).getByRole("row", { name: /AAA/ });
    expect(within(row).getByText("12.30%")).toBeInTheDocument(); // CAGR
    expect(within(row).getByText("15.87%")).toBeInTheDocument(); // annualized volatility
    expect(within(row).getByText("0.050%")).toBeInTheDocument(); // mean daily
    const bbb = within(table).getByRole("row", { name: /BBB/ });
    expect(within(bbb).getAllByText("—").length).toBeGreaterThan(0); // CAGR not annualized
    expect(within(table).getByText("benchmark")).toBeInTheDocument();
    expect(screen.getByText("Analytics: PASS WITH WARNINGS")).toBeInTheDocument();
  });

  it("renders the correlation matrix as a readable table", async () => {
    mockApi(handlers);
    renderRoute("/analytics");
    const matrix = await screen.findByRole("table", { name: /correlation matrix/i });
    expect(within(matrix).getAllByText("-0.30")).toHaveLength(2);
    expect(within(matrix).getAllByText("1.00")).toHaveLength(2);
    expect(within(matrix).getAllByTitle(/AAA vs BBB: -0.3000 \(n = 100\)/)).toHaveLength(1);
  });

  it("switches the statistics sample", async () => {
    const spy = mockApi(handlers);
    const user = userEvent.setup();
    renderRoute("/analytics");
    await user.click(await screen.findByRole("button", { name: "Each series' own history" }));
    expect(await screen.findByText(/Individual samples use each series' own validated dates/)).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("sample=individual"))).toBe(true);
  });

  it("shows the risk-free series as inspection-only", async () => {
    mockApi(handlers);
    renderRoute("/analytics");
    expect(await screen.findByText("Conversion pending approval")).toBeInTheDocument();
    expect(await screen.findByText(/percent per annum, actual\/365/)).toBeInTheDocument();
  });

  it("shows an unavailable state when the backend cannot compute analytics", async () => {
    mockApi({
      ...handlers,
      "/analytics/summary": () => ({ status: 503, body: { code: "DATA_NOT_READY", message: "Required file x.csv is missing.", details: {} } }),
    });
    renderRoute("/analytics");
    expect(await screen.findByText("Descriptive analytics unavailable")).toBeInTheDocument();
    expect(screen.getByText("Required file x.csv is missing.")).toBeInTheDocument();
  });

  it("does not request analytics when the dataset is not ready", async () => {
    const spy = mockApi({ ...handlers, "/data/status": ok(dataMissing) });
    renderRoute("/analytics");
    expect(await screen.findByText("Analysis not available yet")).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("/analytics/"))).toBe(false);
  });
});

describe("dashboard analytics readiness", () => {
  it("summarizes analytics status from the backend", async () => {
    mockApi(handlers);
    renderRoute("/");
    expect(await screen.findByText("Analytics: PASS WITH WARNINGS")).toBeInTheDocument();
    expect(screen.getByText(/100 daily returns/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open descriptive analytics/i })).toHaveAttribute("href", "/analytics");
  });
});
