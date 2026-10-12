import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { analyticsSummary } from "@/test/analyticsFixtures";
import { dataBlocked, dataMissing, dataReady, profiles, universe } from "@/test/fixtures";
import { mockApi, renderRoute } from "@/test/render";

const baseHandlers = {
  "/data/status": () => ({ status: 200, body: dataMissing }),
  "/assets": () => ({ status: 200, body: universe }),
  "/portfolio/profiles": () => ({ status: 200, body: profiles }),
  "/analytics/summary": () => ({ status: 200, body: analyticsSummary }),
};

describe("dashboard", () => {
  it("shows that no dataset is available and lists the asset registry", async () => {
    mockApi(baseHandlers);
    renderRoute("/");
    expect(await screen.findByText("No dataset")).toBeInTheDocument();
    expect(screen.getByText(dataMissing.message)).toBeInTheDocument();
    expect(await screen.findByText("Tata Consultancy Services")).toBeInTheDocument();
    expect(screen.getByText("Unverified")).toBeInTheDocument();
  });

  it("shows validated readiness, coverage and warnings from the pipeline", async () => {
    mockApi({ ...baseHandlers, "/data/status": () => ({ status: 200, body: dataReady }) });
    renderRoute("/");
    expect(await screen.findByText("Ready for analysis")).toBeInTheDocument();
    expect(screen.getByText("Validation: PASS with warnings")).toBeInTheDocument();
    expect(screen.getByText(/1,689/)).toBeInTheDocument();
    expect(screen.getByText("Warnings (1)")).toBeInTheDocument();
    expect(screen.getByText("GSEC")).toBeInTheDocument();
  });

  it("shows critical failures when the dataset is blocked", async () => {
    mockApi({ ...baseHandlers, "/data/status": () => ({ status: 200, body: dataBlocked }) });
    renderRoute("/");
    expect(await screen.findByText("Blocked")).toBeInTheDocument();
    expect(screen.getByText("Validation: BLOCKED")).toBeInTheDocument();
    expect(screen.getByText(/RF_TBILL_91D: not retrieved/)).toBeVisible();
  });

  it("reports an unreachable backend", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    renderRoute("/");
    const alerts = await screen.findAllByRole("alert", {}, { timeout: 5000 });
    expect(alerts[0]).toHaveTextContent(/unable to reach the analytics api/i);
  });
});

describe("CAPM page", () => {
  it("shows the not-ready state instead of results", async () => {
    mockApi(baseHandlers);
    renderRoute("/capm");
    expect(await screen.findByText("Analysis not available yet")).toBeInTheDocument();
  });
});

describe("portfolio page", () => {
  it("only shows the max-volatility input for the growth profile", async () => {
    mockApi(baseHandlers);
    const user = userEvent.setup();
    renderRoute("/portfolio");

    const group = await screen.findByRole("radiogroup", { name: "Investor profile" });
    expect(screen.queryByLabelText(/maximum annualized volatility/i)).not.toBeInTheDocument();

    await user.click(within(group).getByRole("radio", { name: /growth-oriented/i }));
    expect(screen.getByLabelText(/maximum annualized volatility/i)).toBeInTheDocument();

    await user.click(within(group).getByRole("radio", { name: /conservative/i }));
    expect(screen.queryByLabelText(/maximum annualized volatility/i)).not.toBeInTheDocument();
  });

  it("disables optimization while data is not ready", async () => {
    mockApi(baseHandlers);
    renderRoute("/portfolio");
    expect(await screen.findByRole("button", { name: /run optimization/i })).toBeDisabled();
  });

  it("surfaces typed backend errors from the optimizer", async () => {
    mockApi({
      ...baseHandlers,
      "/data/status": () => ({ status: 200, body: dataReady }),
      "/portfolio/optimize": () => ({
        status: 422,
        body: { code: "OPTIMIZATION_FAILED", message: "The optimizer did not converge to a feasible portfolio.", details: {} },
      }),
    });
    const user = userEvent.setup();
    renderRoute("/portfolio");
    const button = await screen.findByRole("button", { name: /run optimization/i });
    await vi.waitFor(() => expect(button).toBeEnabled());
    await user.click(button);
    expect(await screen.findByText(/did not converge to a feasible portfolio/)).toBeInTheDocument();
    expect(screen.getByText("OPTIMIZATION_FAILED")).toBeInTheDocument();
    expect(screen.queryByText("Optimal for these estimates")).not.toBeInTheDocument();
  });

  it("validates sigma_max before calling the API", async () => {
    const fetchSpy = mockApi({
      ...baseHandlers,
      "/data/status": () => ({ status: 200, body: dataReady }),
    });
    const user = userEvent.setup();
    renderRoute("/portfolio");
    await user.click(await screen.findByRole("radio", { name: /growth-oriented/i }));
    const button = screen.getByRole("button", { name: /run optimization/i });
    await vi.waitFor(() => expect(button).toBeEnabled());
    await user.click(button);
    expect(screen.getByText(/enter a maximum volatility/i)).toBeInTheDocument();
    expect(fetchSpy.mock.calls.some(([u]) => String(u).includes("/optimize"))).toBe(false);
  });
});

describe("API client", () => {
  it("reports a timeout distinctly from a network failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new DOMException("signal timed out", "TimeoutError"));
    const { apiClient, ApiError } = await import("@/lib/api-client");
    await expect(apiClient.get("/health")).rejects.toMatchObject({ code: "TIMEOUT" });
    await expect(apiClient.get("/health")).rejects.toBeInstanceOf(ApiError);
  });

  it("maps typed backend errors to ApiError with the backend code", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: "INFEASIBLE_CONSTRAINT", message: "too low", details: { minimum_volatility: 0.035 } }), { status: 422 }),
    );
    const { apiClient } = await import("@/lib/api-client");
    await expect(apiClient.post("/portfolio/optimize", {})).rejects.toMatchObject({
      status: 422,
      code: "INFEASIBLE_CONSTRAINT",
      details: { minimum_volatility: 0.035 },
    });
  });
});
