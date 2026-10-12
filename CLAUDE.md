# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

Academic financial engineering app: CAPM evaluation of six NSE equities against NIFTY 50,
plus MPT / Monte Carlo / SciPy-constrained optimization across 8 assets (6 equities,
G-Sec ETF, gold ETF) for conservative (min-vol), balanced (max-Sharpe) and growth
(max-return s.t. user σ_max) profiles. The classical models are the core. Do not
substitute ML.

**Status: all 8 phases complete (approval items for Phase 2 source decisions in docs/implementation_plan.md). Work proceeds strictly phase by phase**
(see `docs/implementation_plan.md`). Do not start a later phase unless asked.

## Commands

Backend (run from `backend/`; uv manages Python 3.12 and the venv):
- `uv sync`: install from `uv.lock`
- `uv add <pkg>` / `uv add --dev <pkg>`: add dependencies. Never use pip directly.
- `uv run uvicorn app.main:app --reload --port 8000`: dev server
- `uv run pytest`: tests (`tests/unit`, `tests/integration`)
- `uv run ruff check . && uv run ruff format .`: lint and format
- `uv run python -m scripts.download_datasets [--refresh|--offline|--strict]`: data pipeline (exit 1 = BLOCKED)
- `uv run python -m scripts.run_analytics`: persist Phase 3 analytics (run after the pipeline; exit 1 = unavailable or FAILED)
- `uv run python -m scripts.run_capm` / `uv run python -m scripts.run_simulation [--n-portfolios N --seed S]`: persist Phase 4/5 outputs
- `uv run python -m scripts.validate_end_to_end`: full workflow on the real data (exit 1 on any failed check)
- `uv run pytest --run-online tests/online`: optional live-source smoke tests (the default suite is offline)

Frontend (run from `frontend/`):
- `npm install`, `npm run dev` (port 5173, proxies `/api` → `:8000`)
- `npm test`: Vitest. `npm run build`: `tsc -b` + Vite build. `npm run typecheck`

Both: `./scripts/dev.sh`

## Non-negotiable rules

- **No financial calculations in React.** The frontend only formats and displays backend results (`lib/formatters.ts` is display-only).
- **Never fabricate data or results.** No sample or placeholder numbers presented as outputs, no fake successful responses. A missing or invalid dataset returns `DATA_NOT_READY` (503); infeasible user constraints return `INFEASIBLE_CONSTRAINT`; solver failures return `OPTIMIZATION_FAILED` and never show weights.
- **No silent fixes.** Do not forward-fill market prices, relax a user constraint (σ_max), or return an invalid allocation. Report failures with typed errors (`INFEASIBLE_CONSTRAINT`, `OPTIMIZATION_FAILED`).
- **Canonical asset order** = `backend/app/domain/assets.py::ASSET_IDS`. Every vector, matrix and response follows it.
- **Units:** decimals everywhere (0.12 = 12%), annualized with T = 252 from settings. Never mix daily returns, annual yields and annualized returns. Follow `docs/methodology.md`.
- **Reproducibility:** all randomness goes through `numpy.random.default_rng(seed)` with the seed from settings or the request.
- Raw data in `data/raw/` is immutable once downloaded. The backend only treats data as usable when `data/processed/manifest.json` has `validation_passed: true` and matches `data/reports/validation_summary.json`.
- Source decisions (identifier, field, units, limitations) live only in `app/data_pipeline/source_registry.py`. Never "fix" bad source values: flag, exclude and report them.
- Synthetic fixtures (`tests/fixtures/synthetic.py`) are for tests only. Never write them to `data/`.
- Analytics run only on the Phase 2 common sample via `ProcessedDataLoader`; never fill gaps or mix pairwise windows. One return formula: `app/analytics/returns.py` (the pipeline reuses it). Never pass yields through it.
- Never "fix" a non-PSD covariance matrix; report it via `diagnose()` and ask first.
- CAPM, Sharpe and simulation inputs come from `app/services/market_inputs.py` only (one risk-free accrual, one `mu`, one Σ). All annualization is arithmetic ×252; Jensen's alpha must equal 252 × intercept.
- Monte Carlo candidates are "simulation candidates", never "optimal"; the frontier filter is a "Monte Carlo approximation".
- Optimizer results are "optimal for these estimates" only when SLSQP succeeded AND the feasibility checks passed (`analytics/optimization.py::_clean`). Never return last-attempt weights on failure; never default or relax the growth `max_volatility`.

## Backend architecture

`api/routes` (thin) → `services` (orchestration, readiness checks) → `analytics` (pure NumPy/SciPy/statsmodels functions, no I/O) and `data` (read-only repository). `data_pipeline/` is the offline batch pipeline (downloaders → raw store → normalization → cleaning → quality checks → alignment → reporting); request handlers never import it. Static metadata lives in `domain/`, Pydantic contracts in `schemas/`, and settings and errors in `core/`.
- Config: `core/config.py` `Settings`, with env prefix `APP_`. Do not hardcode tunables elsewhere.
- Errors: raise `AppError` subclasses from `core/errors.py`. Handlers produce `ErrorResponse {code, message, details}`.
- Add analytics modules only in the phase that implements them. Do not create empty stubs.
- Tests build the app with `create_app(Settings(data_dir=tmp_path))`. See `tests/conftest.py`.

## Frontend architecture

Feature folders `src/features/{dashboard,capm,portfolio}`, each with `api.ts`, `types.ts`, `hooks/`, `components/` and `page.tsx`.
- HTTP goes through `lib/api-client.ts`, which throws `ApiError` with the backend `code`. Server state uses TanStack Query hooks.
- TS types mirror backend schemas (`src/types/api.ts`, `features/*/types.ts`). Update both sides together.
- Gate results UI with `<RequireData>`; charts render only backend data (Recharts, lazy-loaded pages).
- Styling: Tailwind v4 tokens in `src/styles/index.css` (`bg-surface`, `text-ink-muted`, `text-accent`, …), with light and dark modes. Accessible controls come from `radix-ui`.
- Path alias `@/` → `src/`.

## Docs to keep in sync

Update `docs/architecture.md` (endpoints, structure), `docs/methodology.md` (conventions),
`docs/data_dictionary.md` (files, manifest) and `docs/implementation_plan.md` (phase
status) whenever implementation changes them.
