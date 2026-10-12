import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { dataReady, profiles, universe } from "@/test/fixtures";
import { capmSummary, simulation } from "@/test/phase45Fixtures";
import { mockApi, renderRoute } from "@/test/render";

const ok = (body: unknown) => () => ({ status: 200, body });
const base = { "/data/status": ok(dataReady), "/assets": ok(universe), "/portfolio/profiles": ok(profiles) };

describe("CAPM page", () => {
  it("renders backend estimates and failed regressions explicitly", async () => {
    mockApi({ ...base, "/capm/summary": ok(capmSummary) });
    renderRoute("/capm");
    const table = await screen.findByRole("table", { name: /CAPM estimates/i });
    const aaa = within(table).getByRole("row", { name: /AAA/ });
    expect(within(aaa).getByText("1.20")).toBeInTheDocument(); // beta
    expect(within(aaa).getByText("[1.10, 1.30]")).toBeInTheDocument();
    expect(within(aaa).getByText("13.40%")).toBeInTheDocument(); // CAPM expected
    expect(within(aaa).getByText("2.60%")).toBeInTheDocument(); // Jensen's alpha
    expect(within(aaa).getByText("0.040 (0.060)")).toBeInTheDocument();
    const bbb = within(table).getByRole("row", { name: /BBB/ });
    expect(within(bbb).getByText(/Regression failed: 240 observations/)).toBeInTheDocument();
    expect(screen.getByText("Market risk premium")).toBeInTheDocument();
    expect(screen.getByText("Not a forecast.")).toBeInTheDocument();
  });

  it("shows an error when CAPM cannot be computed", async () => {
    mockApi({ ...base, "/capm/summary": () => ({ status: 503, body: { code: "DATA_NOT_READY", message: "Risk-free rate cannot be aligned.", details: {} } }) });
    renderRoute("/capm");
    expect(await screen.findByText("CAPM analysis unavailable")).toBeInTheDocument();
    expect(screen.getByText("Risk-free rate cannot be aligned.")).toBeInTheDocument();
  });
});

describe("Monte Carlo panel", () => {
  it("defaults to 50,000 portfolios and seed 42 and sends them to the backend", async () => {
    const spy = mockApi({ ...base, "/portfolio/simulate": ok(simulation) });
    const user = userEvent.setup();
    renderRoute("/portfolio");
    expect(await screen.findByLabelText("Number of portfolios")).toHaveValue(50000);
    expect(screen.getByLabelText("Random seed")).toHaveValue(42);
    await user.click(screen.getByRole("button", { name: /run simulation/i }));
    const call = spy.mock.calls.find(([u]) => String(u).includes("/portfolio/simulate"));
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({ n_portfolios: 50000, seed: 42 });

    expect(await screen.findByText("Minimum-volatility candidate")).toBeInTheDocument();
    expect(screen.getByText("Maximum-Sharpe candidate")).toBeInTheDocument();
    expect(screen.getByText("1.45")).toBeInTheDocument(); // max Sharpe from backend
    expect(screen.getByText("50,000")).toBeInTheDocument();
    expect(screen.getAllByText(/not a guaranteed optimum/).length).toBe(2);
    expect(screen.getByText(/Monte Carlo approximation of the efficient frontier/)).toBeInTheDocument();
  });

  it("validates inputs before calling the backend", async () => {
    const spy = mockApi({ ...base, "/portfolio/simulate": ok(simulation) });
    const user = userEvent.setup();
    renderRoute("/portfolio");
    const n = await screen.findByLabelText("Number of portfolios");
    await user.clear(n);
    await user.type(n, "999999");
    await user.click(screen.getByRole("button", { name: /run simulation/i }));
    expect(screen.getByText(/Enter a whole number from 100 to 2,00,000/)).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("/portfolio/simulate"))).toBe(false);
  });

  it("surfaces backend errors", async () => {
    mockApi({ ...base, "/portfolio/simulate": () => ({ status: 503, body: { code: "DATA_NOT_READY", message: "Simulation inputs are invalid: not PSD", details: {} } }) });
    const user = userEvent.setup();
    renderRoute("/portfolio");
    await user.click(await screen.findByRole("button", { name: /run simulation/i }));
    expect(await screen.findByText("Simulation inputs are invalid: not PSD")).toBeInTheDocument();
  });
});
