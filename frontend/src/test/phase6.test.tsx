import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { dataReady, profiles, universe } from "@/test/fixtures";
import { capmSummary, simulation } from "@/test/phase45Fixtures";
import { frontier, optimization } from "@/test/phase6Fixtures";
import { mockApi, renderRoute } from "@/test/render";

const ok = (body: unknown) => () => ({ status: 200, body });

function handlers(optimize: (init?: RequestInit) => { status: number; body: unknown }) {
  return {
    "/data/status": ok(dataReady),
    "/assets": ok(universe),
    "/portfolio/profiles": ok(profiles),
    "/portfolio/simulate": ok(simulation),
    "/portfolio/frontier?points=30": ok(frontier),
    "/portfolio/optimize": optimize,
  };
}

const byProfile = (init?: RequestInit) => {
  const body = JSON.parse(String(init?.body));
  return { status: 200, body: optimization(body.profile) };
};

describe("portfolio optimization", () => {
  it("runs the selected profile and shows metrics, solver status and the Monte Carlo comparison", async () => {
    const spy = mockApi(handlers(byProfile));
    const user = userEvent.setup();
    renderRoute("/portfolio");
    await user.click(await screen.findByRole("button", { name: /run optimization/i }));
    expect(await screen.findByText("Balanced portfolio")).toBeInTheDocument();
    expect(screen.getByText("Optimal for these estimates")).toBeInTheDocument();
    expect(screen.getByText(/Solver converged · all constraints satisfied/)).toBeInTheDocument();
    const comparison = screen.getByRole("table", { name: /compared with the Monte Carlo candidate/i });
    expect(within(comparison).getByText("+0.03")).toBeInTheDocument(); // Sharpe difference from backend
    const body = JSON.parse(String(spy.mock.calls.find(([u]) => String(u).includes("/optimize"))?.[1]?.body));
    expect(body).toEqual({ profile: "balanced" });
  });

  it("sends the user's volatility limit for the growth profile and never a default", async () => {
    const spy = mockApi(handlers(byProfile));
    const user = userEvent.setup();
    renderRoute("/portfolio");
    await user.click(await screen.findByRole("radio", { name: /growth-oriented/i }));
    await user.click(screen.getByRole("button", { name: /run optimization/i }));
    expect(screen.getByText(/enter a maximum volatility/i)).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("/optimize"))).toBe(false);
    await user.type(screen.getByLabelText(/maximum annualized volatility/i), "12");
    await user.click(screen.getByRole("button", { name: /run optimization/i }));
    expect(await screen.findByText("Growth-oriented portfolio")).toBeInTheDocument();
    const call = spy.mock.calls.find(([u]) => String(u).includes("/optimize"));
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({ profile: "growth", max_volatility: 0.12 });
  });

  it("keeps the previous result visible when a later request is infeasible", async () => {
    let calls = 0;
    mockApi(
      handlers((init) => {
        calls += 1;
        if (calls === 1) return byProfile(init);
        return {
          status: 422,
          body: { code: "INFEASIBLE_CONSTRAINT", message: "the minimum achievable annualized volatility is 3.5485%", details: { minimum_volatility: 0.035 } },
        };
      }),
    );
    const user = userEvent.setup();
    renderRoute("/portfolio");
    await user.click(await screen.findByRole("radio", { name: /growth-oriented/i }));
    await user.type(screen.getByLabelText(/maximum annualized volatility/i), "12");
    await user.click(screen.getByRole("button", { name: /run optimization/i }));
    expect(await screen.findByText("Growth-oriented portfolio")).toBeInTheDocument();
    const input = screen.getByLabelText(/maximum annualized volatility/i);
    await user.clear(input);
    await user.type(input, "1");
    await user.click(screen.getByRole("button", { name: /run optimization/i }));
    expect(await screen.findByText(/minimum achievable annualized volatility is 3.5485%/)).toBeInTheDocument();
    expect(screen.getByText("INFEASIBLE_CONSTRAINT")).toBeInTheDocument();
    expect(screen.getByText(/showing the previous result/)).toBeInTheDocument();
    expect(screen.getByText("Growth-oriented portfolio")).toBeInTheDocument();
  });

  it("compares profiles side by side once two are optimized", async () => {
    mockApi(handlers(byProfile));
    const user = userEvent.setup();
    renderRoute("/portfolio");
    await user.click(await screen.findByRole("button", { name: /run optimization/i }));
    await screen.findByText("Balanced portfolio");
    expect(screen.getByText(/Optimize at least two profiles/)).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /conservative/i }));
    await user.click(screen.getByRole("button", { name: /run optimization/i }));
    const table = await screen.findByRole("table", { name: /profiles side by side/i });
    expect(within(table).getByText("8.10%")).toBeInTheDocument();
    expect(within(table).getByText("16.77%")).toBeInTheDocument();
  });
});

describe("CAPM detail views", () => {
  it("shows the selected equity's regression output and distinguishes intercept from alpha", async () => {
    mockApi({ ...handlers(byProfile), "/capm/summary": ok(capmSummary) });
    renderRoute("/capm");
    expect(await screen.findByText("Equity detail")).toBeInTheDocument();
    expect(screen.getByText("Estimate per trading day")).toBeInTheDocument();
    expect(screen.getByText("Annualized (× 252)")).toBeInTheDocument();
    expect(screen.getByText("Market beta with 95% confidence intervals")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Equity" })).toHaveValue("AAA"); // failed equity excluded
  });
});
