# Architecture

## Overview

A monorepo with a Python analytics API and a React client. The two are strictly separated:
**every financial calculation runs in the backend**, and the frontend only requests,
validates input for, and displays backend results.

```
Browser ──► Vite dev server (/api proxy) ──► FastAPI  /api/v1/*
                                               │
                     routes (thin) ──► services (orchestration) ──► analytics (pure math)
                                               │
                                               └──► data.repository ──► data/processed/
```

## Backend (`backend/`)

| Package | Responsibility | May import |
|---|---|---|
| `app/api` | HTTP routes, dependency wiring. Validate, delegate, serialize. No logic. | services, schemas, domain, core |
| `app/services` | Orchestrate one use case: check data readiness, load inputs, call analytics, build response schemas. | analytics, data, domain, schemas, core |
| `app/analytics` | Pure, side-effect-free financial functions over NumPy/pandas objects. No I/O, no HTTP, no Pydantic. | domain, NumPy/pandas/SciPy/statsmodels |
| `app/data` | Read-only access to processed data: `repository.py` (manifest and validation summary), `loader.py` (`ProcessedDataLoader` → `ValidatedDataset`), `validation.py` (CSV schema checks, `DatasetLoadError`). | domain |
| `app/data_pipeline` | Phase 2 acquisition pipeline: source registry, downloaders, raw store, normalization, cleaning, quality checks, alignment, reporting, CLI. Batch process; never imported by request handlers. | core, domain |
| `app/domain` | Static metadata: asset registry and investor profiles. | (none) |
| `app/schemas` | Pydantic request/response contracts. | domain |
| `app/core` | Settings, logging, error types and handlers. | schemas |

Imports flow in one direction (api → services → analytics/data → domain), which prevents cycles.

### Canonical asset ordering

`app.domain.assets.PORTFOLIO_ASSETS` defines the only asset order. Price and return
matrices, `mu`, `Sigma`, optimizer weight vectors and API responses all follow
`ASSET_IDS`. Analytics functions take this ordering as a precondition. Services enforce it
when loading data.

### Configuration

`app/core/config.py` holds a single `Settings` object (pydantic-settings). Each field can be
overridden with an `APP_`-prefixed environment variable or a root `.env` file. It holds the
study period, the annualization constant (252 trading days), Monte Carlo defaults and the
random seed. `create_app(settings)` accepts an explicit `Settings`, so tests inject a
temporary data directory.

### Error model

Every error response uses one schema: `ErrorResponse {code, message, details}`.

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body/query failed schema validation (e.g. growth without `max_volatility`). |
| `DATA_NOT_READY` | 503 | No validated dataset (`manifest.json` missing, invalid or failed). |
| `NOT_IMPLEMENTED` | 501 | Endpoint reserved for a later phase. |
| `INFEASIBLE_CONSTRAINT` | 422 | User constraint admits no feasible portfolio (Phase 6). |
| `OPTIMIZATION_FAILED` | 422 | Solver did not converge to a valid allocation (Phase 6). |

Services raise typed `AppError` subclasses. Handlers in `app/core/errors.py` map them to
responses, so analysis endpoints never return fabricated "successful" results.

### Endpoints

| Method | Path | Phase | Status |
|---|---|---|---|
| GET | `/api/v1/health` | 1 | Implemented |
| GET | `/api/v1/data/status` | 1–2 | Implemented: overall status, per-dataset coverage and checks, common period, warnings, limitations |
| GET | `/api/v1/assets` | 1 | Implemented (registry metadata) |
| GET | `/api/v1/portfolio/profiles` | 1 | Implemented (profile metadata) |
| GET | `/api/v1/analytics/summary` | 3 | Analytics status, checks, sample, conventions, risk-free profile |
| GET | `/api/v1/analytics/statistics?sample=common\|individual&series=…` | 3 | Descriptive statistics per series |
| GET | `/api/v1/analytics/correlation` | 3 | 8×8 correlation, pairwise counts, diagnostics |
| GET | `/api/v1/analytics/covariance?frequency=daily\|annualized` | 3 | 8×8 covariance and diagnostics |
| GET | `/api/v1/analytics/returns?series=…&start=YYYY-MM-DD&end=…` | 3 | Daily returns (columnar) and `sessions_spanned` |
| GET | `/api/v1/analytics/distribution?series=X&sample=…&bins=5..200` | 3 | Histogram computed by the backend |
| GET | `/api/v1/analytics/risk-free` | 3 | Native weekly yields and inspection profile (no conversion) |
| GET | `/api/v1/capm/summary` | 4 | Reserved: 503 / 501 |
| POST | `/api/v1/portfolio/simulate` | 5 | Reserved: 422 / 503 / 501 |
| POST | `/api/v1/portfolio/optimize` | 6 | Reserved: 422 / 503 / 501 |

Interactive OpenAPI docs are served at `http://localhost:8000/docs`.

## Descriptive analytics (Phase 3)

```
ProcessedDataLoader (app/data) ──► compute_analytics (app/services) ──► app/analytics (pure)
        │ schema + readiness checks          │ checks, cache per dataset version
        └─ DatasetLoadError → 503            └─► analytics_queries → schemas → routes
```

- `AnalyticsService.result()` loads the validated dataset and computes everything once
  per Phase 2 manifest timestamp (in-process cache), so the API always reflects the
  current artifacts.
- `scripts/run_analytics.py` persists the same results under `data/processed/`.
- Unknown series or bad parameters return 422 `VALIDATION_ERROR`. A missing or invalid
  dataset returns 503 `DATA_NOT_READY` with the failing file named.
- The frontend's `/analytics` page (lazy-loaded with Recharts) only formats values; the
  histogram bins are computed by the backend.

## Data pipeline (Phase 2)

```
source_registry ─► downloaders ─► raw_store (immutable snapshots)
                                     │
normalization ─► cleaning (flag → exclude) ─► cross_source ─► quality_checks
                                                                   │
                       alignment (inner join, no filling) ─► reporting ─► manifest.json (last)
```

- `source_registry.py` holds every source decision: identifier, URL, selected field,
  units, frequency, corporate actions and known limitations.
- Downloaders return `RawSnapshot`s or raise `DownloadError`. A failed source is recorded
  as `NOT_RETRIEVED`, and no placeholder file is ever written.
- `DataPipeline` accepts injected downloaders, so tests run the full pipeline offline
  against synthetic fixtures (`backend/tests/fixtures/synthetic.py`).

## Frontend (`frontend/`)

React 19 + TypeScript (strict) + Vite, with Tailwind CSS v4 for styling, Radix
primitives (`radix-ui`) for accessible controls, TanStack Query for server state and
loading/error handling, React Router for navigation, and Recharts (installed, used from
Phase 7) for charts.

```
src/
  app/            providers (QueryClient), route table, browser router
  components/     layout (shell, sidebar), common (Card, EmptyState, ErrorAlert, RequireData, …), charts (ChartFrame)
  features/       dashboard | capm | portfolio — each with api.ts, types.ts, hooks/, components/, page.tsx
  hooks/          data hooks shared across features (dataset status, asset universe)
  lib/            api-client (typed fetch + ApiError), formatters (display only), query keys
  types/          TypeScript mirrors of shared backend schemas
  styles/         Tailwind entry + design tokens (light/dark)
  test/           Vitest setup, render helpers, metadata-only fixtures
```

- `lib/api-client.ts` turns every non-2xx response into an `ApiError` carrying the backend
  `code`, so the UI can tell "data not ready" apart from "not implemented" and from
  validation failures.
- `RequireData` gates any results area on `/data/status`. When the dataset is missing, the
  UI shows an explicit empty state, never placeholder numbers.
- `ChartFrame` renders an empty state until it receives real backend results.
- Investor-profile labels and formulations come from `/portfolio/profiles`, so the
  frontend does not duplicate domain definitions.
- `formatters.ts` performs display formatting only (percent, dates).

## Deviations from the initial target structure

| Change | Reason |
|---|---|
| Repository root is the monorepo root (no extra `financial-engineering-portfolio/` folder). | The git repository already is the project. Nesting would add a meaningless level. |
| `analytics/` holds only a package docstring for now. `returns.py`, `capm.py`, etc. are added in the phase that implements them. | The spec says "do not create empty abstractions". Empty stubs would imply functionality that does not exist. |
| Validation lives in `app/data_pipeline/` (not `app/data/validation.py`). | The pipeline is a batch process with its own modules; `app/data` stays a thin read-only layer for the API. |
| Downloaders: `yahoo_finance.py`, `fund_nav.py` (AMFI), `risk_free.py` (RBI Handbook) and `holidays.py` (RBI holiday matrix); no `nse.py`. | NSE rejects automated clients (HTTP 403), so no NSE client exists. |
| Data CLI in `backend/scripts/` (`python -m scripts.download_datasets`). | It must run as a module inside the backend's uv environment. The root `scripts/` folder holds developer shell scripts. |
| Added `core/errors.py` and `api/dependencies.py`. | Centralized error mapping and dependency injection keep routes thin and testable. |
| Added `api/routes/assets.py` and `GET /portfolio/profiles`. | The UI needs registry and profile metadata without hardcoding it. |
| `app/routes.tsx` split from `app/router.tsx`; shared hooks in `src/hooks/`. | Tests reuse the route table with a memory router. Data-status hooks are used by several features. |
| `frontend/tsconfig.app.json` / `tsconfig.node.json` alongside `tsconfig.json`. | Standard Vite project-reference split between browser and Node (config) code. |
