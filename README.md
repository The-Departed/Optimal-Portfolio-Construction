# CAPM-Based Equity Performance Evaluation and Multi-Asset Portfolio Optimization

An academic financial engineering application. It evaluates six Indian equities against
NIFTY 50 with the **Capital Asset Pricing Model**, and builds long-only portfolios across
equities, a government-bond ETF and a gold ETF. The portfolio work uses **Modern Portfolio
Theory**, **Monte Carlo simulation** and **constrained numerical optimization** for three
investor profiles (conservative, balanced, growth-oriented).

> **Status: Phases 4–5 (CAPM and Monte Carlo simulation) complete.** Constrained
> optimization for the investor profiles is Phase 6 and not yet implemented.
> See [docs/implementation_plan.md](docs/implementation_plan.md) and
> [data/reports/data_quality_report.md](data/reports/data_quality_report.md).

## Repository layout

```
backend/    FastAPI + Pydantic + NumPy/pandas/SciPy/statsmodels  (uv-managed)
frontend/   React + TypeScript + Vite + Tailwind + TanStack Query + Recharts  (npm)
data/       raw / interim / processed / reports  (see data/README.md)
docs/       architecture, methodology, data dictionary, implementation plan
scripts/    developer scripts
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/). It installs Python 3.12 automatically from `backend/.python-version`.
- Node.js ≥ 20 with npm.

## Setup

```bash
cp .env.example .env               # optional; defaults work out of the box

cd backend && uv sync              # creates backend/.venv from uv.lock
cd ../frontend && npm install      # installs from package-lock.json
```

## Build the dataset

```bash
cd backend
uv run python -m scripts.download_datasets   # acquire, clean, validate, align (about 3 minutes on first run)
```

Then compute the descriptive analytics (returns, statistics, correlation and covariance):

```bash
uv run python -m scripts.run_analytics       # writes data/processed/{returns,metadata}/…
```

Then CAPM and the Monte Carlo simulation:

```bash
uv run python -m scripts.run_capm                                  # data/processed/metadata/capm_*
uv run python -m scripts.run_simulation --n-portfolios 50000 --seed 42   # data/processed/simulations/
```

The API computes the same results on demand; the scripts persist them. Rerunning the
pipeline reuses the immutable raw snapshots. Use `--refresh` to download new snapshots,
or `--offline` to rebuild without the network. The data-quality report is written to
`data/reports/`.

## Run

```bash
./scripts/dev.sh                   # backend :8000 + frontend :5173
```

Or run each side separately:

```bash
cd backend  && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

- UI: http://localhost:5173. Vite proxies `/api` to the backend.
- API docs: http://localhost:8000/docs
- Health: `curl http://localhost:8000/api/v1/health`

## Test and build

```bash
cd backend  && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd backend  && uv run pytest --run-online tests/online   # optional live-source smoke tests
cd frontend && npm test && npm run build
```

## Documentation

- [Architecture](docs/architecture.md): layers, API, error model, frontend structure
- [Methodology](docs/methodology.md): return, annualization, risk-free, CAPM, MPT, simulation and optimizer conventions
- [Data dictionary](docs/data_dictionary.md): instruments, planned files, manifest contract
- [Implementation plan](docs/implementation_plan.md): phases and status
