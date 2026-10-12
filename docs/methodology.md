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
- **Proposed daily alignment (to be confirmed in Phase 3):** for each aligned return
  interval (t−1, t], take the most recent yield whose auction date is on or before t−1 (an
  as-of join on information available at the start of the interval). Accrue it over the
  interval's calendar days on the series' own basis: `rf_t = y/100 × days(t−1, t)/365`.
  This handles weekends, holidays and multi-session intervals consistently. It carries a
  published reference rate forward between auctions; it does not create daily market
  observations. Auctions from the month before the study start are retained for this lookup.
- **Phase 3 status:** the series is inspected, not converted. The checks confirm units
  (percent per annum, actual/365), weekly frequency (median gap 7 days, maximum 22), 360
  auctions in the study period plus 4 lookback auctions, and a range of 2.93–7.05%. No
  daily risk-free series is created: the conversion above awaits approval and will be
  applied in Phase 4. The analytics layer refuses to pass a yield series through the
  price-return formula (`NotAPriceSeriesError`).
- Annualized `R_f` for Sharpe ratios and CAPM will be derived from the same `rf_t` series,
  annualized consistently with `mu`.
- The government-bond ETF is a **risky asset** in the portfolio. It is not the risk-free
  asset.

## 5. CAPM (Objective 1)

For each equity *i* and trading day *t*:

- Excess returns: `x_{i,t} = r_{i,t} − rf_d,t` and `x_{m,t} = r_{m,t} − rf_d,t`.
- OLS (statsmodels): `x_{i,t} = a_i + beta_i · x_{m,t} + e_{i,t}`.
- CAPM-implied expected return: `E(R_i) = R_f + beta_i · (E(R_m) − R_f)`, with
  `E(R_m) = T · mean(r_{m,d})`.
- Jensen's alpha (annualized): `alpha_i = T · a_i`. Because OLS residuals have mean zero,
  this equals `mu_i − E(R_i)` exactly, so alpha is consistent with the CAPM figure shown.
- Diagnostics: R², t-statistics and p-values for `a` and `beta`, standard error of `beta`,
  number of observations, and Durbin–Watson. Newey–West (HAC) standard errors are
  reported as a robustness check. **(Phase 4)**

The CAPM module evaluates individual equities only. It is not the multi-asset optimizer.

## 6. Portfolio metrics (Objective 2)

For weights `w` (canonical order), `mu` and `Sigma` as in §3:

- `R_p = wᵀ mu`
- `sigma_p = sqrt(wᵀ Sigma w)`
- `Sharpe = (R_p − R_f) / sigma_p`

Constraints for all profiles: `Σ w_i = 1` and `0 ≤ w_i ≤ 1` (no short selling).

## 7. Monte Carlo simulation (Phase 5)

- Default 50,000 allocations, configurable seed (`APP_RANDOM_SEED`), and
  `numpy.random.default_rng(seed)`.
- Weights are drawn from `Dirichlet(1, …, 1)`, the uniform distribution on the long-only
  simplex. Every draw is feasible by construction.
- Metrics for all draws are computed in vectorized form.
- The opportunity set is shown as a risk/return scatter coloured by Sharpe ratio. The
  empirical frontier is estimated as the upper envelope of simulated points within
  volatility bins.
- Limitation: uniform sampling rarely reaches simplex corners or edges, where optima often
  lie. Monte Carlo is a search and visualisation method, not an optimizer. It is
  therefore compared against §8.

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
