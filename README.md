# CAPM-Based Equity Performance Evaluation and Multi-Asset Portfolio Optimization

An academic financial engineering application:

- **CAPM**: evaluates six NSE-listed Indian equities against NIFTY 50 (beta, CAPM-implied
  return, Jensen's alpha and regression diagnostics).
- **Modern Portfolio Theory**: builds long-only portfolios across eight assets (six
  equities, a government-bond ETF and a gold ETF).
- **Monte Carlo simulation**: explores the space of feasible allocations.
- **Constrained numerical optimization**: finds the portfolio for three investor profiles.

| Profile | Objective |
|---|---|
| Conservative | Minimize annualized volatility |
| Balanced | Maximize the Sharpe ratio |
| Growth-oriented | Maximize expected return subject to a **user-defined** maximum volatility |

> **Status:** all eight implementation phases are complete. Results are **historical
> estimates, not forecasts or investment advice.** Four source decisions from Phase 2 are
> documented as approval items (see [Known limitations](#known-limitations)).

---

## Contents

- [Data and coverage](#data-and-coverage)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Run instructions](#run-instructions)
- [Tests and checks](#tests-and-checks)
- [Demonstration workflow](#demonstration-workflow)
- [Reproducibility](#reproducibility)
- [API endpoints](#api-endpoints)
- [Known limitations](#known-limitations)
- [Documentation](#documentation)

---

## Data and coverage

| Asset | Identifier | Source | Field |
|---|---|---|---|
| Mahindra & Mahindra, HDFC Bank, TCS, Reliance, Hindustan Unilever, Sun Pharma | `M&M.NS`, `HDFCBANK.NS`, `TCS.NS`, `RELIANCE.NS`, `HINDUNILVR.NS`, `SUNPHARMA.NS` | Yahoo Finance | Adjusted close |
| Government bonds: Nippon India ETF Nifty 8-13 yr G-Sec (`LTGILTBEES`) | AMFI scheme 139496, ISIN INF204KB1882 | AMFI | Daily NAV |
| Gold: Nippon India ETF Gold BeES | `GOLDBEES.NS`, ISIN INF204KB17I5 | Yahoo Finance | Adjusted close |
| Benchmark: NIFTY 50 (price index) | `^NSEI` | Yahoo Finance | Close |
| Risk-free rate: 91-day T-bill auction implicit yield | RBI Handbook of Statistics | RBI | % p.a., weekly |

**Study period** requested: 2019-01-01 to 2025-12-31.

**Common sample** (all 8 assets and NIFTY 50): 2019-01-02 to 2025-12-31, giving 1,690
prices and **1,689 daily returns**. All CAPM, Monte Carlo and optimization results use
this sample.

**Validation status:** `PASS_WITH_WARNINGS`. Details are in
[`data/reports/data_quality_report.md`](data/reports/data_quality_report.md).

Downloaded data is git-ignored, so a fresh clone must run the data pipeline once (see
below). No API keys or credentials are needed.

## Architecture

```
frontend/  React + TypeScript + Vite + Tailwind + Recharts   (display only: no financial maths)
   │  /api/v1  (Vite dev proxy)
backend/   FastAPI + Pydantic
   ├─ app/api          thin routes
   ├─ app/services     orchestration, validation, caching (analytics, CAPM, simulation, optimization)
   ├─ app/analytics    pure NumPy / pandas / SciPy / statsmodels functions
   ├─ app/data         read-only loading and schema checks of processed data
   └─ app/data_pipeline  offline acquisition, cleaning and validation (Phase 2)
data/      raw/ (immutable) · interim/ · processed/ · reports/ (tracked)
docs/      architecture · methodology · data dictionary · implementation plan
```

Details: [docs/architecture.md](docs/architecture.md).

## Requirements

- **[uv](https://docs.astral.sh/uv/)** for the backend. It installs Python 3.12
  automatically from `backend/.python-version`.
- **Node.js ≥ 20** and **npm** for the frontend.
- Internet access only for the first data download.

## Run instructions

All commands start from the repository root.

### 1. Install dependencies

```bash
# Backend (creates backend/.venv from the lockfile)
cd backend
uv sync
cd ..

# Frontend
cd frontend
npm install
cd ..

# Optional: local configuration (every value has a working default)
cp .env.example .env
```

### 2. Build the dataset and analyses (first run)

```bash
cd backend
uv run python -m scripts.download_datasets   # download, clean, validate and align (~3 min the first time)
uv run python -m scripts.run_analytics       # Phase 3: returns, statistics, correlation, covariance
uv run python -m scripts.run_capm            # Phase 4: CAPM for the six equities
uv run python -m scripts.run_simulation      # Phase 5: 50,000 portfolios, seed 42
cd ..
```

`download_datasets` exits with 0 for PASS or PASS_WITH_WARNINGS and 1 if the dataset is
BLOCKED. Later runs reuse the saved raw downloads. Use `--refresh` to download again, or
`--offline` to rebuild without the network.

The analysis scripts only *save* results to `data/processed/`; the API computes the same
results on demand. Run them again after rebuilding the dataset.

### 3. Start the backend

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000/api/v1>
- Interactive API docs: <http://localhost:8000/docs>
- Health check: `curl http://localhost:8000/api/v1/health`

### 4. Start the frontend (in a second terminal)

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. The Vite dev server forwards `/api` to `http://127.0.0.1:8000`.

### Both at once

```bash
./scripts/dev.sh          # backend on :8000 and frontend on :5173; Ctrl+C stops both
```

### Production build of the frontend

```bash
cd frontend
npm run build             # type-check + bundle into frontend/dist
npm run preview           # serve the build locally (backend must be running)
```

## Tests and checks

```bash
# Backend: unit, pipeline and API integration tests (offline, synthetic fixtures)
cd backend
uv run pytest
uv run ruff check . && uv run ruff format --check .

# End-to-end workflow on the real dataset (offline; needs step 2)
uv run python -m scripts.validate_end_to_end

# Optional: smoke tests against the live data sources
uv run pytest --run-online tests/online

# Frontend
cd ../frontend
npm test                  # Vitest + Testing Library
npm run build             # includes the TypeScript check
```

## Demonstration workflow

1. **Dashboard** (`/`): confirm *Ready for analysis*, the coverage period, 1,689 daily
   returns and 8 portfolio assets. Open *Warnings* and *Known limitations*.
2. **Descriptive analytics** (`/analytics`):
   - statistics for each asset (daily and annualized)
   - CAGR and volatility charts
   - the correlation heatmap and table
   - return histograms
   - the risk-free series
3. **CAPM analysis** (`/capm`):
   - Read the market inputs (R_f 5.57%, E(R_m) 14.83%).
   - Read the results table: beta with its 95% CI, CAPM E(R), Jensen's alpha and R².
   - Compare the historical-vs-CAPM chart and the beta chart.
   - Pick an equity in *Equity detail* to see its regression intercept (daily and ×252)
     next to Jensen's alpha.
4. **Monte Carlo** (`/portfolio`, top card): keep **50,000** portfolios and seed **42**,
   then click **Run simulation**. You'll see:
   - the risk-return scatter
   - the frontier approximation from the sample
   - the minimum-volatility and maximum-Sharpe *simulation candidates*
5. **Optimize each investor profile** (`/portfolio`, *Investor profile optimization*):
   - **Conservative**: select it and click **Run optimization**. Expect about 3.55%
     volatility, mostly GSEC. Compare with the Monte Carlo candidate (4.74%).
   - **Balanced**: Sharpe about 1.48, versus 1.45 for the best simulated portfolio.
   - **Growth-oriented**: enter a maximum volatility, e.g. `12` (%), then run. The result
     sits on the 12% limit (about 23.1% return). Then try `2` to see the explicit
     *infeasible* message (minimum achievable volatility 3.55%). The previous result
     stays visible.
   - Inspect each result's allocation, weights, solver status, constraint checks, the
     Monte Carlo comparison and methodology. Check the risk-return chart (exact frontier
     plus the optimized points) and the *Profile comparison* table.

## Reproducibility

- Raw downloads are immutable and checksummed (`data/raw/…/metadata.json`). Rebuilding
  with `--offline` reproduces every processed file from them.
- Monte Carlo uses `numpy.random.default_rng(seed)`. The same dataset, portfolio count
  and seed give identical portfolios, and this is verified on every run. The full output
  goes to `data/processed/simulations/mc_n<N>_seed<S>.csv.gz`.
- The optimizer's random starting points use a fixed seed (20240101). All solver
  settings are returned in every response.
- Conventions (×252 annualization, ddof = 1, CAGR on 365.25 days, risk-free accrual) are
  recorded in `analytics_summary.json` and in API responses.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/data/status` | Dataset readiness, per-dataset validation, warnings |
| GET | `/api/v1/assets` | Asset registry |
| GET | `/api/v1/analytics/{summary,statistics,correlation,covariance,returns,distribution,risk-free}` | Phase 3 analytics |
| GET | `/api/v1/capm/summary?equities=…` | CAPM for the six equities |
| GET | `/api/v1/portfolio/profiles` | Investor-profile definitions |
| POST | `/api/v1/portfolio/simulate` | Monte Carlo `{n_portfolios: 100–200000, seed, scatter_points}` |
| POST | `/api/v1/portfolio/optimize` | `{profile, max_volatility (growth only, decimal), simulation_portfolios?, simulation_seed?}` |
| GET | `/api/v1/portfolio/frontier?points=5–100` | Exact long-only efficient frontier |

Errors share one shape, `{code, message, details}`:

| HTTP | Code | Meaning |
|---|---|---|
| 422 | `VALIDATION_ERROR` | Invalid input |
| 422 | `INFEASIBLE_CONSTRAINT` | The growth limit is below the minimum achievable volatility |
| 422 | `OPTIMIZATION_FAILED` | The solver did not converge to a feasible portfolio |
| 503 | `DATA_NOT_READY` | The dataset is missing or invalid |

## Known limitations

- **Historical estimates.** Expected returns are historical arithmetic means and the
  covariance is the unshrunk sample estimate. Optimal weights are sensitive to estimation
  error and are not forecasts.
- **Annualization.** All annualization uses ×252. The common sample has about 242 return
  intervals per year, so annualized figures sit about 4% above per-calendar-year values.
  For example, the annualized R_f is 5.57% against an average quoted yield of 5.33%.
  Returns, risk and R_f are scaled consistently.
- **Benchmark.** NIFTY 50 is a price index, while equity returns include dividends. This
  overstates Jensen's alpha by about β × the index dividend yield. No historical alpha is
  significant at 5%.
- **Risk-free rate.** Weekly 91-day T-bill auction yields are carried forward (at most 20
  days) and accrued daily. This approximates a short rate.
- **Data gaps.** Yahoo is missing two NSE sessions in 2019 (13 Feb and 29 Mar) across
  all series. The bond ETF uses NAV because its exchange price is illiquid. Two corrupt
  gold rows are excluded. 38 of the 1,689 returns span more than one session.
- **Monte Carlo.** Candidates are the best of a finite sample, not optima. The optimizer
  is optimal only for these estimates, ignoring costs, taxes, liquidity and rebalancing.
- **Pending approval.** Four Phase 2 source decisions are still awaiting approval: NAV for
  the bond ETF, the gold-row exclusion, the price-index benchmark and the risk-free
  conversion.

## Documentation

- [docs/architecture.md](docs/architecture.md): layers, endpoints, error model, data pipeline
- [docs/methodology.md](docs/methodology.md): returns, statistics, risk-free rate, CAPM,
  portfolio metrics, Monte Carlo, optimization, validation
- [docs/data_dictionary.md](docs/data_dictionary.md): every dataset, file and column
- [docs/implementation_plan.md](docs/implementation_plan.md): phases, results, approval items
- [data/reports/data_quality_report.md](data/reports/data_quality_report.md): data validation report
