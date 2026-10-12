# Implementation plan

| Phase | Scope | Status |
|---|---|---|
| 1 | Project scaffold and architecture | **Complete** |
| 2 | Data acquisition and validation | **Complete** (PASS_WITH_WARNINGS; approvals pending) |
| 3 | Financial data and descriptive analytics | **Complete** (analytics PASS_WITH_WARNINGS) |
| 4 | CAPM equity evaluation | **Complete** |
| 5 | Monte Carlo portfolio simulation | **Complete** |
| 6 | Constrained optimization | Not started |
| 7 | Frontend integration and visualization | Not started |
| 8 | Validation and final delivery | Not started |

## Phase 1 — scaffold (complete)

- FastAPI app factory, settings, logging, typed error model.
- Endpoints: health, data status (manifest-based), asset registry, profile definitions.
- Reserved analysis endpoints return `DATA_NOT_READY` (503) or `NOT_IMPLEMENTED` (501), never fabricated values.
- Typed Pydantic schemas for CAPM, simulation and optimization requests/responses.
- Asset registry with all eight assets plus benchmark and risk-free metadata, all marked unverified.
- React/TS/Vite/Tailwind shell: Dashboard, CAPM and Portfolio pages with loading, error and empty states. The investor-profile selector shows σ_max for growth only.
- Backend tests (pytest), frontend tests (Vitest + Testing Library), production build, CI workflow.

## Phase 2 — data acquisition and validation (complete)

- Pipeline `backend/app/data_pipeline/`, run through `python -m scripts.download_datasets`.
- Sources verified: Yahoo Finance (6 equities, NIFTY 50, GOLDBEES), AMFI NAV (LTGILTBEES,
  GOLDBEES), RBI Handbook (91-day T-bill auctions), RBI holiday matrix (Mumbai).
- Result: **PASS_WITH_WARNINGS**. The common sample runs from 2019-01-02 to 2025-12-31:
  1,690 dates and 1,689 daily returns (97.7% of reference sessions).
- `/api/v1/data/status` and the dashboard report the real validation status.

**Decisions awaiting approval (needed before Phase 4 uses the risk-free rate and benchmark)**

1. Government bonds use the ETF's AMFI NAV, because the NSE price is too illiquid.
2. Two corrupt Yahoo GOLDBEES rows (2019-12-19 and 2019-12-20) are excluded, not repaired.
3. The benchmark is the NIFTY 50 price index; no accessible Total Return Index exists.
4. The risk-free rate is the weekly 91-day T-bill auction yield, aligned using the as-of
   accrual in `methodology.md` §4.
5. Missing NAVs on RBI Mumbai holidays and weekend special sessions are treated as
   non-valuation days and drop out of the common sample (40 sessions in total, together
   with the gold and NIFTY gaps).
6. Yahoo lacks two probable NSE sessions (2019-02-13, 2019-03-29) in every series; the
   following returns span two sessions.

## Phase 3 — descriptive analytics (complete)

- Data access: `app/data/loader.py` and `validation.py`, reading only manifest-referenced,
  schema-checked files.
- Analytics: `app/analytics/{conventions,returns,statistics,covariance,risk_free}.py`.
  Orchestration lives in `app/services/analytics_service.py`.
- API: `/api/v1/analytics/{summary,statistics,correlation,covariance,returns,distribution,risk-free}`.
- UI: a `/analytics` page and a dashboard readiness card.
- Outputs: 7 files under `data/processed/` (see `data_dictionary.md`).
- Result on real data: **PASS_WITH_WARNINGS**. The checks pass; the warnings are the 38
  multi-session returns, the pending risk-free conversion, and the upstream Phase 2
  warnings.

## Phases 4–5 — CAPM and Monte Carlo (complete)

- CAPM: `app/analytics/capm.py`, `app/services/capm_service.py`, `/api/v1/capm/summary`,
  and the `/capm` page. All six regressions were estimated on 1,689 daily intervals
  (2019-01-03 to 2025-12-31). Betas range from 0.57 to 1.10 and R² from 0.17 to 0.58; no
  intercept is significant at 5%.
- Risk-free: the as-of accrual convention from methodology §4 is adopted (annualized
  `R_f` 5.57%); formal approval is still pending.
- Monte Carlo: `app/analytics/{portfolio_metrics,monte_carlo,efficient_frontier}.py`,
  `app/services/simulation_service.py`, `/api/v1/portfolio/simulate`, and the
  `/portfolio` page.
- Default run (50,000 portfolios, seed 42): all checks pass.
  - Minimum-volatility candidate: 4.74% volatility, 11.76% return.
  - Maximum-Sharpe candidate: Sharpe 1.45, 17.93% return, 8.50% volatility.
  - Frontier approximation: 61 portfolios.

## Phases 6–8

See the specification. Each phase adds its analytics module(s), service wiring and tests,
then replaces the corresponding `NOT_IMPLEMENTED` response.
