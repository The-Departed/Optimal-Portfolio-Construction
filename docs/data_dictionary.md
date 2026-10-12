# Data dictionary

Status: **Phase 2 complete.** All files below are produced by
`uv run python -m scripts.download_datasets` (from `backend/`). The authoritative
definitions live in `backend/app/data_pipeline/source_registry.py`.

## Datasets

| ID | Instrument | Role | Source | Identifier | Field used | Units | Frequency |
|---|---|---|---|---|---|---|---|
| `MM` | Mahindra & Mahindra | portfolio asset | Yahoo Finance | `M&M.NS` | Adj Close | INR/share (adjusted) | daily |
| `HDFCBANK` | HDFC Bank | portfolio asset | Yahoo Finance | `HDFCBANK.NS` | Adj Close | INR/share (adjusted) | daily |
| `TCS` | Tata Consultancy Services | portfolio asset | Yahoo Finance | `TCS.NS` | Adj Close | INR/share (adjusted) | daily |
| `RELIANCE` | Reliance Industries | portfolio asset | Yahoo Finance | `RELIANCE.NS` | Adj Close | INR/share (adjusted) | daily |
| `HINDUNILVR` | Hindustan Unilever | portfolio asset | Yahoo Finance | `HINDUNILVR.NS` | Adj Close | INR/share (adjusted) | daily |
| `SUNPHARMA` | Sun Pharmaceutical Industries | portfolio asset | Yahoo Finance | `SUNPHARMA.NS` | Adj Close | INR/share (adjusted) | daily |
| `GSEC` | Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt | portfolio asset | AMFI NAV history | scheme `139496`, ISIN `INF204KB1882`, NSE `LTGILTBEES` | Net Asset Value | INR/unit | daily (fund business days) |
| `GOLD` | Nippon India ETF Gold BeES | portfolio asset | Yahoo Finance | `GOLDBEES.NS` (ISIN `INF204KB17I5`) | Adj Close | INR/unit (split-adjusted) | daily |
| `NIFTY50` | NIFTY 50 (price index) | benchmark | Yahoo Finance | `^NSEI` | Close | index points | daily |
| `RF_TBILL_91D` | 91-day GoI T-bill, implicit yield at cut-off | risk-free | RBI Handbook of Statistics | table "Auctions of 91-Day Government of India Treasury Bills" | Implicit Yield at Cut-off Price (percent) | % p.a., actual/365 | weekly (auctions) |
| `GSEC_EXCHANGE` | LTGILTBEES NSE price | cross-check only | Yahoo Finance | `LTGILTBEES.NS` | Close | INR/unit | daily (traded days) |
| `GOLD_NAV` | Gold BeES NAV | cross-check only | AMFI NAV history | scheme `140088` | Net Asset Value | INR/unit (unadjusted) | daily |
| `RBI_HOLIDAYS_MUMBAI` | RBI bank holidays, Mumbai | calendar evidence | RBI Holiday Matrix | regional office 28 | holiday date/name | dates | annual lists |

Canonical asset order (all aligned files): `MM, HDFCBANK, TCS, RELIANCE, HINDUNILVR,
SUNPHARMA, GSEC, GOLD`. NIFTY 50 is kept in separate benchmark files.

## Files

### `data/raw/<category>/<dataset_id>/<YYYYMMDDTHHMMSSZ>/`

Downloads are stored verbatim (Yahoo CSV + response metadata, AMFI text lines for the
scheme, RBI HTML pages), with a `metadata.json` holding the request, retrieval time
(UTC), pipeline version and a SHA-256 for each file. Snapshots are never modified. Later
runs reuse the newest snapshot unless `--refresh` is passed.

### `data/interim/prices/<id>.csv`, `data/interim/risk_free/<id>.csv`

Every normalized record, including invalid ones, with flags: `is_missing`,
`is_non_numeric`, `is_non_finite`, `is_invalid_date`, `is_duplicate_date`, `excluded`,
`exclusion_reason`. Cross-checked series also carry `reference_value` and
`reference_deviation`.

### `data/processed/`

| File | Columns | Notes |
|---|---|---|
| `prices/<id>.csv` | `date`, `adj_close` / `nav` / `close` | Cleaned individual series, study period only |
| `returns/<id>.csv` | `date`, `simple_return`, `sessions_spanned` | Returns over consecutive valid observations of that series |
| `prices/portfolio_prices_aligned.csv` | `date`, 8 asset IDs | Common dates only |
| `prices/benchmark_prices_aligned.csv` | `date`, `NIFTY50` | Same dates as above |
| `returns/portfolio_returns_aligned.csv` | `date`, 8 asset IDs | Simple daily returns; first date dropped |
| `returns/benchmark_returns_aligned.csv` | `date`, `NIFTY50` | Same dates as above |
| `risk_free/RF_TBILL_91D.csv` | `auction_date`, `issue_date`, `implicit_yield_pct`, `cut_off_price`, `in_study_period`, `handbook_edition`, `rbi_page_id` | Native weekly frequency; includes lookback auctions before the study start |
| `metadata/return_intervals.csv` | `date`, `sessions_spanned` | > 1 when the aligned return spans dropped sessions |
| `metadata/alignment.json` | — | Common period, dropped sessions by dataset, calendar findings |
| `metadata/datasets.json` | — | Per-dataset source metadata (same as the source manifest) |
| `manifest.json` | — | Readiness contract, see below |

### Phase 3 outputs (`uv run python -m scripts.run_analytics`)

These are derived from the Phase 2 files above and never overwrite them. A Phase 2
pipeline run deletes them, because they would be stale; rerun the analytics afterwards.

| File | Contents |
|---|---|
| `returns/asset_daily_returns.csv` | `date`, 8 asset IDs: simple daily returns on the common sample (equal to `portfolio_returns_aligned.csv` within 1e-12, which is checked) |
| `returns/benchmark_daily_returns.csv` | `date`, `NIFTY50` |
| `metadata/descriptive_statistics.csv` | One row per series and sample (`sample` = `common` / `individual`): `observations`, `start`, `end`, `mean_daily`, `median_daily`, `std_daily`, `min_daily`, `max_daily`, `skewness`, `excess_kurtosis`, `cumulative_return`, `annualized_return` (CAGR), `annualized_mean_return`, `annualized_volatility`, `elapsed_calendar_days`, `notes` |
| `metadata/correlation_matrix.csv` | 8×8 Pearson correlation, `asset_id` index, canonical order |
| `metadata/daily_covariance_matrix.csv` | 8×8 sample covariance of daily returns |
| `metadata/annualized_covariance_matrix.csv` | Daily covariance × 252 |
| `metadata/analytics_summary.json` | Analytics version, timestamp, status, checks, source-dataset references (Phase 2 manifest timestamp and files), sample, conventions, missing-data policy, matrix diagnostics, risk-free profile |

All values are decimals at full precision; rounding happens only in the UI.

### `data/reports/`

`data_quality_report.md` (human-readable), `validation_summary.json`,
`source_manifest.json`, `coverage_report.csv`, `missing_values_report.csv`,
`excluded_records.csv`, `extreme_returns_report.csv`, `cross_source_report.csv`.

## Manifest and readiness contract

`data/processed/manifest.json` is written **last**, and is deleted at the start of every
run, so an interrupted run never leaves a stale "ready" flag.

```json
{
  "schema_version": 1,
  "pipeline_version": "2.0.0",
  "generated_at": "ISO-8601",
  "validation_passed": true,
  "overall_status": "PASS | PASS_WITH_WARNINGS | BLOCKED",
  "study_period": {"start": "2019-01-01", "end": "2025-12-31"},
  "common_period": {"first": "...", "last": "...", "price_dates": 0, "return_observations": 0},
  "files": {"portfolio_returns_aligned": "data/processed/returns/portfolio_returns_aligned.csv"},
  "reports": {"validation_summary": "data/reports/validation_summary.json"}
}
```

`GET /api/v1/data/status` returns `ready: true` only when the manifest has
`validation_passed: true` **and** `validation_summary.json` exists with the same
`overall_status`.

| Artifacts | `state` | `ready` |
|---|---|---|
| manifest absent | `missing` | false |
| manifest or summary unparseable, missing, or inconsistent | `invalid` | false |
| `overall_status: BLOCKED` | `validation_failed` | false |
| `PASS` / `PASS_WITH_WARNINGS` | `ready` | true |
