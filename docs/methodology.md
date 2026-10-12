# Financial methodology

This document fixes the conventions used by the pipeline (Phase 2) and the conventions
that later phases implement. No financial statistics have been computed yet. Items marked
**(Phase N)** are decided in that phase. Historical statistics are descriptive, not
forecasts.

## 1. Notation and units

- All rates and returns are **decimals** (0.12 = 12%), both internally and in the API.
  Exception: the processed risk-free file keeps the source's percent units
  (`implicit_yield_pct`) and is converted to decimals in Phase 3.
- `T = 252` trading days per year (`APP_TRADING_DAYS_PER_YEAR`).
- `d` subscript = daily; unsubscripted annual quantities are annualized.
- Asset vectors follow the canonical order in `app/domain/assets.py`.

## 2. Returns (implemented in Phase 2)

- **Equities:** simple daily returns from Yahoo `Adj Close` (split-, bonus- and
  dividend-adjusted): `r_t = P_t / P_{t-1} − 1`.
- **Government bonds:** simple daily returns of the LTGILTBEES ETF **NAV** (AMFI scheme
  139496). The NSE exchange price was evaluated and rejected because the ETF is thinly
  traded: 92.2% session coverage, a 109-session gap in 2019, and return correlation 0.34
  with NAV. Yield changes are *never* used as a substitute for investment returns.
- **Gold:** simple daily returns of the Gold BeES ETF exchange price (Yahoo, split-adjusted).
  Two records that Yahoo divided by 100 twice (2019-12-19 and 2019-12-20) are excluded as
  source errors after cross-checking against AMFI NAV. They are not repaired.
- **Benchmark:** simple daily returns of NIFTY 50. This is a price index: no accessible
  source provides the Total Return Index. **Limitation:** equity returns include dividends
  but the benchmark's do not.
- Each series is cleaned on its own first; then all eight assets and NIFTY 50 are aligned
  on the **intersection** of their dates. Nothing is forward-filled, interpolated or
  zero-filled. A date missing from any series is dropped for all of them, and the next
  return spans the gap (`processed/metadata/return_intervals.csv`, `sessions_spanned`).
- Debt-ETF NAVs are not published on RBI Mumbai bank holidays, because the G-sec market is
  closed. Those dates (verified against RBI's holiday matrix) are treated as expected
  non-valuation days and are dropped from the common sample.

Simple (not log) returns are used because portfolio returns are weight-additive in simple
returns (`R_p = Σ w_i r_i`), which is what the MPT formulas assume.

## 3. Descriptive statistics and annualization (implemented in Phase 3)

Implementation: `backend/app/analytics/` (`returns.py`, `statistics.py`, `covariance.py`,
`conventions.py`). All conventions are recorded in `analytics_summary.json`.

**Samples.** The primary sample is the Phase 2 *common sample*: the dates on which all
eight assets and NIFTY 50 have a validated price (2019-01-02 to 2025-12-31, 1,690 prices,
1,689 returns). Every statistic used downstream, and every correlation and covariance,
comes from this one sample. *Individual-sample* statistics use each series' own validated
dates. They are reported for description only; GSEC, for example, has 1,697 returns
because its own history has different gaps. Nothing is filled. The 38 common-sample
returns that span more than one session are kept as single observations and listed in
`return_intervals.csv`.

| Quantity | Estimator / formula |
|---|---|
| Daily return | `r_t = P_t / P_(t-1) − 1`; the first date has no return |
| Mean, median, min, max | Of daily returns |
| Daily standard deviation | Sample estimator, ddof = 1 |
| Skewness | Adjusted Fisher–Pearson G1 (`scipy.stats.skew(bias=False)`) |
| Excess kurtosis | Sample-adjusted G2 (`scipy.stats.kurtosis(fisher=True, bias=False)`); normal = 0 |
| Cumulative return | `P_end / P_start − 1` over the sample's first and last prices |
| Historical annualized return (CAGR) | `(P_end / P_start)^(365.25 / elapsed_calendar_days) − 1`; not reported for intervals shorter than 365 days (`APP_ANALYTICS_MIN_ANNUALIZATION_DAYS`) |
| Annualized arithmetic mean | `mean(r_d) × 252`; reported separately because it differs from CAGR, and it is the MPT input `mu` (Phase 5) |
| Annualized volatility | `std(r_d) × √252` |
| Correlation | Pearson, common sample only |
| Covariance | Sample covariance (ddof = 1) on the common sample; annualized = daily × 252 |

**Edge cases.** Statistics that cannot be estimated are returned as `null` with a note,
never as zero. This covers fewer than 2, 3 or 4 observations for std, skew and kurtosis;
a constant series, detected by exact equality, which leaves skew and kurtosis undefined;
and an interval too short to annualize. Missing returns raise an error rather than being
skipped or zero-filled.

**Matrix validation.** Labels must follow the canonical asset order. Matrices must be
symmetric (within 1e-12 relative), finite, and positive semidefinite (minimum eigenvalue
≥ −1e-10 × maximum). A correlation matrix must also have a unit diagonal and entries in
[−1, 1]. Pairwise sample sizes are reported and must all equal the common-sample size.
A failed check is **reported, never repaired**: no nearest-PSD adjustment is applied
without approval. Actual result: correlation minimum eigenvalue 0.53, annualized
covariance minimum eigenvalue 1.3e-3.

Historical returns and risk estimates are descriptive. They do not forecast future
performance, and a low historical correlation does not guarantee future diversification.

## 4. Risk-free rate

- **Series (Phase 2):** RBI *Handbook of Statistics on Indian Economy*, table "Auctions of
  91-Day Government of India Treasury Bills", column *Implicit Yield at Cut-off Price
  (percent)*. Units: percent per annum on an actual/365 basis. These are primary-auction
  yields at **weekly** frequency, not a daily secondary-market yield. Each Handbook edition
  covers about one fiscal year; the 2019–2026 editions are combined, and where editions
  overlap the latest one is kept (35 overlapping auctions, all identical). Stored at native
  frequency in `processed/risk_free/RF_TBILL_91D.csv`.
- Validation: units (median about 5.5, i.e. percent), weekly cadence, gaps between
  auctions, and agreement with the yield recomputed from the cut-off price,
  `(100/P − 1) × 365/91` (maximum deviation 0.021 pp).
- **Daily alignment (adopted in Phase 4; formal approval still pending).** Implemented in
  `app/analytics/risk_free.py::accrued_risk_free`. For each aligned return interval
  (t−1, t], take the most recent yield whose auction date is on or before t−1 (an as-of
  join on information available when the interval starts). Accrue it over the interval's
  calendar days on the series' own basis: `rf_t = y/100 × days(t−1, t)/365` (simple
  interest, actual/365). Weekends, holidays and multi-session intervals are handled
  consistently. Intervals with no prior auction, or whose latest auction is more than 35
  days old, raise an error rather than being filled. The original weekly observations are
  kept unchanged; no daily yield is created.
- **Approximation.** A 91-day primary-auction yield is a term rate used as a short-rate
  proxy, carried forward for up to 20 days in the actual sample.
- **Annualization:** `R_f = 252 × mean(rf_t)` = **5.57%**, so that `R_f`, `mu` and the
  covariance share the same ×252 scaling, keeping excess returns and Sharpe ratios
  internally consistent. Caveat: the common sample has about 241.6 return intervals per
  year (dropped sessions and NSE's ~248 sessions), so ×252 annualized figures sit about
  4% above per-calendar-year values. For example, the average quoted yield is 5.33%.
- Phase 3 only inspects the series. The analytics layer refuses to pass a yield series
  through the price-return formula (`NotAPriceSeriesError`).
- The government-bond ETF is a **risky asset** in the portfolio. It is not the risk-free
  asset.

## 5. CAPM (Objective 1, implemented in Phase 4)

Code: `app/analytics/capm.py`, `app/services/capm_service.py`, `GET /api/v1/capm/summary`,
and `scripts/run_capm.py`.

For each of the six equities, on the common sample (1,689 daily intervals, 2019-01-03 to
2025-12-31), with identical dates for every variable:

- Regression (OLS, statsmodels): `R_i,t − R_f,t = a_i + β_i (R_m,t − R_f,t) + ε_i,t`.
  `R_i` is the equity's simple return, `R_m` the NIFTY 50 (price-index) return, and
  `R_f` the accrued risk-free return (§4).
- Every annualized input uses the arithmetic convention with T = 252:
  `E(R_m) = T·mean(R_m)`, `R_f = T·mean(R_f)`, and historical mean return
  `T·mean(R_i)`.
- CAPM expected return: `E(R_i) = R_f + β_i (E(R_m) − R_f)`.
- **Jensen's alpha** = historical annualized mean return − `E(R_i)` (annualized).
- The **regression intercept** `a_i` is reported separately in daily units (decimal per
  trading interval) and annualized as `T·a_i`. Under these conventions the two are
  identical: because OLS residuals have mean zero, `T·a_i = T·mean(x_i) − β_i T·mean(x_m)`.
  The service checks the identity (tolerance 1e-10) and marks the equity failed if it does
  not hold.
- CAGR is shown for reference but is not used in alpha, because it is a geometric quantity
  and would mix conventions.
- Diagnostics: OLS standard errors, t-statistics, p-values and 95% CIs for `a` and `β`;
  Newey–West HAC p-values with lags = ⌊4(n/100)^(2/9)⌋ (7 here) as a robustness check;
  R², adjusted R², residual standard deviation (daily and annualized), and Durbin–Watson.
- Failure handling: fewer than 60 observations, a constant market excess return,
  misaligned or missing data, or non-finite estimates all raise `CapmEstimationError`.
  The equity is then reported as `failed` with every metric null.
- Limitations:
  - The benchmark is a price index while the equity returns include dividends. This
    understates `E(R_m)` and overstates alpha by roughly β × the index dividend yield.
  - The risk-free proxy is described in §4.
  - A non-zero historical alpha (none is significant at 5% here) does not show that a
    stock is mispriced, and is not a forecast.

The CAPM module evaluates individual equities only. It is not the multi-asset optimizer.

## 6. Portfolio metrics (Objective 2, implemented in Phase 5)

Code: `app/analytics/portfolio_metrics.py`. For weight rows `w` in canonical order,
`mu` = annualized arithmetic mean returns (§3), `Sigma` = annualized sample covariance,
and `R_f` from §4:

- `R_p = wᵀ mu`, `σ_p = sqrt(wᵀ Σ w)`, `Sharpe = (R_p − R_f) / σ_p`.
- Constraints: `0 ≤ w_i ≤ 1` and `Σ w_i = 1` (tolerance 1e-9); violations raise.
- Variance round-off within −1e-12 × max|Σ| is reported as 0. Anything more negative
  means Σ is not PSD and raises.
- If `σ_p < 1e-10`, the Sharpe ratio is undefined: it is returned as null and excluded
  from the maximum-Sharpe search, never as ±inf.

## 7. Monte Carlo simulation (implemented in Phase 5)

Code: `app/analytics/monte_carlo.py`, `efficient_frontier.py`,
`app/services/simulation_service.py`, `POST /api/v1/portfolio/simulate`, and
`scripts/run_simulation.py`.

- **Sampling:** weights are drawn from a symmetric `Dirichlet(1, …, 1)`, the uniform
  distribution on the long-only simplex, with `numpy.random.default_rng(seed)`. Every draw
  is positive and sums to 1, and is still validated.
- **Parameters:** default 50,000 portfolios and seed 42 (`APP_MONTE_CARLO_SIMULATIONS`,
  `APP_RANDOM_SEED`). The API accepts 100–200,000 portfolios
  (`APP_MAX_MONTE_CARLO_SIMULATIONS`) and seeds 0–2³²−1. The same dataset, count and seed
  reproduce identical results, which is checked on every run.
- **Inputs:** `mu` and `Σ` come from Phase 3 on the common sample. Σ must pass the
  symmetry and PSD checks, otherwise the simulation stops; it is never repaired. CAPM
  returns are **not** substituted for `mu`.
- **Outputs:**
  - All portfolios (id, 8 weights, return, volatility, Sharpe) are written to
    `data/processed/simulations/mc_n<N>_seed<S>.csv.gz`, with a JSON file holding the
    inputs and metadata.
  - The API returns distribution summaries, the two candidates (minimum volatility and
    maximum Sharpe), a deterministic plotting subsample (the first `scatter_points` draws,
    which is unbiased because draws are i.i.d.), the frontier approximation, and the
    validation checks.
- **Monte Carlo frontier approximation:** the non-dominated sampled portfolios. A portfolio
  is kept if no other sampled portfolio has volatility ≤ and return ≥ with one strict
  inequality, using a return tolerance of 1e-12. This is **not** the exact efficient
  frontier; Phase 6 computes that by constrained optimization.
- **Limitations:**
  - The candidates are the best of a finite sample, not global optima.
  - Uniform sampling rarely reaches corners and edges of the simplex.
  - Historical mean returns are noisy, and high-Sharpe portfolios are sensitive to them.
  - The sample covariance is unshrunk.
  - None of these results are forecasts.

## 8. Constrained optimization (Phase 6)

SciPy `minimize(method="SLSQP")` with bounds `[0, 1]` and the equality `Σw = 1`, started
from equal weights and from additional feasible starts.

| Profile | Objective | Extra constraint |
|---|---|---|
| Conservative | minimize `sqrt(wᵀ Sigma w)` | none |
| Balanced | maximize `(wᵀ mu − R_f) / sqrt(wᵀ Sigma w)`, solved as minimizing the negative | guard for `sigma_p < eps` |
| Growth | maximize `wᵀ mu` | `sqrt(wᵀ Sigma w) ≤ sigma_max` (user input) |

- **Feasibility (growth):** if `sigma_max` is below the minimum-variance portfolio's
  volatility, the API returns `INFEASIBLE_CONSTRAINT` together with that minimum. The
  constraint is never relaxed silently.
- **Post-solve validation:** the solver must report success, the weights must satisfy the
  bounds and the sum within `1e-8`, and the volatility constraint must hold within
  tolerance. Otherwise the API returns `OPTIMIZATION_FAILED`. Sub-tolerance negative
  round-off is clipped to zero and renormalized. This step is reported, not hidden.
- **Analytical efficient frontier:** minimize variance over a grid of target returns
  between the minimum-variance return and `max(mu)`.
- **Comparison:** each optimizer result is reported next to the best simulated portfolio
  for the same objective. The optimizer should be at least as good, and the gap is shown.

## 9. Planned mathematical tests

Weights sum to one, all weights lie in [0, 1], variance ≥ 0 within tolerance, and the
variance formula responds correctly to covariance perturbations. CAPM inputs share the
same frequency. Simulation is reproducible for a fixed seed. Optimizer outputs satisfy
all constraints, and infeasible or failed optimizations are reported explicitly.
