# Data-quality report — Phase 2

Generated 2026-10-12T12:41:32+00:00 by pipeline v2.0.0. This file is regenerated on every run; do not edit by hand.

## 1. Executive summary

**Overall status: `PASS_WITH_WARNINGS`** — ready for Phase 3: **yes**.

- Requested study period: 2019-01-01 to 2025-12-31.
- Common sample (8 assets + NIFTY 50): 2019-01-02 to 2025-12-31, 1690 price dates / 1689 daily returns (97.69% of reference sessions).
- Critical failures: 0; warnings: 19; documented limitations: 20.

## 2. Sources used

| Dataset | Role | Source | Selected field | Retrieval | Retrieved (UTC) |
|---|---|---|---|---|---|
| MM | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:26:31+00:00 |
| HDFCBANK | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:26:32+00:00 |
| TCS | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:26:34+00:00 |
| RELIANCE | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:26:36+00:00 |
| HINDUNILVR | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:26:38+00:00 |
| SUNPHARMA | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:26:39+00:00 |
| GSEC | portfolio_asset | AMFI (Association of Mutual Funds in India) NAV history | Net Asset Value | cached | 2026-10-12T12:27:25+00:00 |
| GOLD | portfolio_asset | Yahoo Finance (chart API via yfinance) | Adj Close | cached | 2026-10-12T12:27:26+00:00 |
| NIFTY50 | benchmark | Yahoo Finance (chart API via yfinance) | Close | cached | 2026-10-12T12:27:28+00:00 |
| RF_TBILL_91D | risk_free | Reserve Bank of India, Handbook of Statistics on Indian Economy | Implicit Yield at Cut-off Price (percent) | cached | 2026-10-12T12:28:05+00:00 |
| GSEC_EXCHANGE | cross_check | Yahoo Finance (chart API via yfinance) | Close | cached | 2026-10-12T12:28:07+00:00 |
| GOLD_NAV | cross_check | AMFI (Association of Mutual Funds in India) NAV history | Net Asset Value | cached | 2026-10-12T12:28:07+00:00 |
| RBI_HOLIDAYS_MUMBAI | calendar_reference | Reserve Bank of India, Holiday Matrix | Holiday | cached | 2026-10-12T12:33:40+00:00 |

Source decisions:

- **Equities** — Yahoo Finance via `yfinance` (`Adj Close`, split- and dividend-adjusted). NSE was the planned cross-check but rejects automated clients (HTTP 403), so no independent equity source was available.
- **NIFTY 50** — Yahoo Finance `^NSEI` (price index). NSE / NSE Indices historical endpoints are not accessible to automated clients.
- **Government bonds** — AMFI daily NAV of the LTGILTBEES ETF. The NSE exchange price (Yahoo `LTGILTBEES.NS`) was retrieved and rejected as the return series because the ETF is thinly traded (see §8 and the `GSEC_EXCHANGE` row). This is the same instrument, not a substitution.
- **Gold** — Yahoo Finance `GOLDBEES.NS` exchange price, cross-checked against AMFI NAV.
- **Risk-free rate** — RBI *Handbook of Statistics on Indian Economy*, table 'Auctions of 91-Day Government of India Treasury Bills', one HTML table per annual edition on www.rbi.org.in. DBIE has no public API and rbidocs.rbi.org.in file downloads are behind a CAPTCHA, so the Handbook tables (the same RBI data) are used.

## 3. Identifiers verified

| Dataset | Instrument | Identifier | Other identifiers | Identity check |
|---|---|---|---|---|
| MM | Mahindra & Mahindra | M&M.NS | — | pass: Source reports 'Mahindra & Mahindra Limited' |
| HDFCBANK | HDFC Bank | HDFCBANK.NS | — | pass: Source reports 'HDFC Bank Limited' |
| TCS | Tata Consultancy Services | TCS.NS | — | pass: Source reports 'Tata Consultancy Services Limited' |
| RELIANCE | Reliance Industries | RELIANCE.NS | — | pass: Source reports 'Reliance Industries Limited' |
| HINDUNILVR | Hindustan Unilever | HINDUNILVR.NS | — | pass: Source reports 'Hindustan Unilever Limited' |
| SUNPHARMA | Sun Pharmaceutical Industries | SUNPHARMA.NS | — | pass: Source reports 'Sun Pharmaceutical Industries Limited' |
| GSEC | Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt | 139496 | mf=21, isin=INF204KB1882, nse_symbol=LTGILTBEES | pass: Scheme 139496, ISIN INF204KB1882 |
| GOLD | Nippon India ETF Gold BeES | GOLDBEES.NS | — | pass: Source reports 'Nippon India ETF Gold BeES' |
| NIFTY50 | NIFTY 50 | ^NSEI | — | pass: Source reports 'NIFTY 50' |
| RF_TBILL_91D | 91-Day Government of India Treasury Bill - implicit yield at cut-off price | Auctions of 91-Day Government of India Treasury Bills | — | pass: 8 edition page(s) titled 'Auctions of 91-Day Government of India Treasury Bills' |
| GSEC_EXCHANGE | LTGILTBEES NSE exchange price (cross-check) | LTGILTBEES.NS | — | pass: Source reports 'Nippon India Mutual Fund - Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt' |
| GOLD_NAV | Nippon India ETF Gold BeES NAV (cross-check) | 140088 | mf=21, isin=INF204KB17I5, nse_symbol=GOLDBEES | pass: Scheme 140088, ISIN INF204KB17I5 |
| RBI_HOLIDAYS_MUMBAI | RBI holiday list - Mumbai regional office | Mumbai (regional office 28) | regional_office=28 | pass: 7 yearly page(s) for 'Mumbai regional office' |

## 4. Date coverage by instrument

| Dataset | First | Last | Obs. | Missing sessions | Session coverage | Covers period | Status |
|---|---|---|---|---|---|---|---|
| MM | 2019-01-01 | 2025-12-31 | 1730 | 0 | 100.00% | True | PASS_WITH_WARNINGS |
| HDFCBANK | 2019-01-01 | 2025-12-31 | 1730 | 0 | 100.00% | True | PASS |
| TCS | 2019-01-01 | 2025-12-31 | 1730 | 0 | 100.00% | True | PASS |
| RELIANCE | 2019-01-01 | 2025-12-31 | 1730 | 0 | 100.00% | True | PASS |
| HINDUNILVR | 2019-01-01 | 2025-12-31 | 1730 | 0 | 100.00% | True | PASS |
| SUNPHARMA | 2019-01-01 | 2025-12-31 | 1730 | 0 | 100.00% | True | PASS |
| GSEC | 2019-01-01 | 2025-12-31 | 1698 | 0 | 100.00% | True | PASS_WITH_WARNINGS |
| GOLD | 2019-01-01 | 2025-12-31 | 1727 | 3 | 99.83% | True | PASS_WITH_WARNINGS |
| NIFTY50 | 2019-01-02 | 2025-12-31 | 1727 | 3 | 99.83% | True | PASS_WITH_WARNINGS |
| RF_TBILL_91D | 2019-01-02 | 2025-12-24 | 360 | n/a | n/a | True | PASS_WITH_WARNINGS |
| GSEC_EXCHANGE | 2019-01-04 | 2025-12-31 | 1595 | 135 | 92.20% | True | FAIL |
| GOLD_NAV | 2019-01-01 | 2025-12-31 | 1729 | 0 | 100.00% | True | PASS_WITH_WARNINGS |
| RBI_HOLIDAYS_MUMBAI | 2019-01-26 | 2025-12-25 | 153 | n/a | n/a | n/a | PASS |

Session coverage is measured against the reference NSE calendar: the union of trading dates in the six equity series (1730 sessions, including special Muhurat sessions). The risk-free series is weekly and is measured by auction cadence instead.

## 5. Data-cleaning decisions

- Dates are normalized to timezone-naive exchange-local (Asia/Kolkata) dates; original timestamps are kept in `source_timestamp`.
- Values are parsed without coercion: explicit missing markers (`-`, `N.A.`, empty) and non-numeric text are flagged, not converted.
- Records are **flagged then excluded** for: invalid date, missing value, non-numeric, non-finite, non-positive price (or yield outside 0–20%), conflicting duplicate dates, and source errors (gold only: deviation >20% from split-adjusted NAV). Identical duplicates keep one record. For the risk-free series, overlapping Handbook editions keep the latest edition.
- No forward-filling, interpolation or zero-filled returns. Extreme returns are flagged and retained.
- Daily simple returns `r_t = P_t / P_(t-1) - 1` are computed from cleaned series; nothing is annualized in this phase. Yields are never passed through the return formula.

Excluded records (all are listed in `excluded_records.csv`):

| Dataset | Excluded | By reason |
|---|---|---|
| GOLD | 2 | {'source_error': 2} |
| RF_TBILL_91D | 38 | {'duplicate_identical': 35, 'missing_value': 3} |

## 6. Missing values and gaps

| Dataset | Missing values (raw) | Missing sessions (unexplained) | Non-valuation days (explained) | Longest missing run | Longest gap (days) | Missing session dates |
|---|---|---|---|---|---|---|
| MM | 0 | 0 | 0 | 0 | 5 | — |
| HDFCBANK | 0 | 0 | 0 | 0 | 5 | — |
| TCS | 0 | 0 | 0 | 0 | 5 | — |
| RELIANCE | 0 | 0 | 0 | 0 | 5 | — |
| HINDUNILVR | 0 | 0 | 0 | 0 | 5 | — |
| SUNPHARMA | 0 | 0 | 0 | 0 | 5 | — |
| GSEC | 0 | 0 | 36 | 0 | 5 | — |
| GOLD | 0 | 3 | 0 | 2 | 5 | 2019-12-19, 2019-12-20, 2025-10-24 |
| NIFTY50 | 0 | 3 | 0 | 1 | 5 | 2019-01-01, 2019-10-27, 2020-11-14 |
| RF_TBILL_91D | 3 | — | — | — | 22 | — |
| GSEC_EXCHANGE | 0 | 135 | 0 | 109 | 167 | 2019-01-01, 2019-01-02, 2019-01-03, 2019-01-07, 2019-01-08, 2019-01-09, 2019-01-10, 2019-01-11, 2019-01-14, 2019-01-15, 2019-01-16, 2019-01-17 … (+123) |
| GOLD_NAV | 0 | 0 | 6 | 0 | 5 | — |
| RBI_HOLIDAYS_MUMBAI | 0 | — | — | — | n/a | — |


**Non-valuation days (AMFI NAV series only).** AMFI does not publish a NAV on days that are not fund business days. A missing NAV on an NSE session is classified as *explained* only if the date is (a) a weekend special NSE session (Muhurat / Budget-day trading) or (b) listed in RBI's official Mumbai holiday matrix (`RBI_HOLIDAYS_MUMBAI`), when the government-securities market is closed. Explained dates are excluded from the coverage ratio but are **not filled**: they drop out of the common sample. Any other missing date counts against coverage.


**Reference-calendar gaps.** The reference calendar is built from the Yahoo equity series, so a session missing from *every* Yahoo series is invisible to per-series checks. Weekdays that are not RBI Mumbai holidays but on which AMFI struck a NAV are reported as probable NSE sessions missing from Yahoo: 2019-02-13, 2019-03-29. On these dates no equity, index or gold price exists in the source, so the following return in every series spans two sessions (not reflected in `sessions_spanned`, which uses the Yahoo-derived calendar).

## 7. Corporate-action considerations

- Equities use Yahoo `Adj Close`, which back-adjusts for splits, bonus issues and cash dividends. No manual adjustments are applied on top. Split/bonus events in the period (HDFC Bank 2019 and 2025, Reliance 2024) are covered by the automated discontinuity check (any daily return beyond +/-50% fails). The Reliance -> Jio Financial demerger (ex-date 2023-07-20) is too small for that check and was inspected manually during source verification: the Yahoo series shows -0.12% on 2023-07-20, i.e. the spin-off value is already reflected in the adjusted history.
- Adjusted-close levels depend on the download date (later dividends rescale history); returns do not. The raw snapshot is reused on later runs for reproducibility.
- Gold BeES: 1:100 unit split, exchange ex-date 2019-12-19; AMFI NAV per unit changes from 2019-12-23. Yahoo's back-adjusted series is used as delivered; the NAV is divided by 100 before 2019-12-23 **only for the cross-check**.
- The G-Sec ETF and gold ETF are growth ETFs with no distributions in the period; NIFTY 50 is a price index (dividends excluded).

## 8. Cross-source checks

| Primary | Reference | Matched dates | Median abs dev | P95 abs dev | Max abs dev | Days >5% | Return corr. | Excluded source errors |
|---|---|---|---|---|---|---|---|---|
| GSEC | GSEC_EXCHANGE | 1561 | 0.137% | 0.621% | 16.1% (2020-03-16) | 3 | 0.3377 | 0 |
| GOLD | GOLD_NAV | 1721 | 0.277% | 2.057% | 5.8% (2020-03-25) | 4 | 0.8808 | 2 |

- **GSEC** — expected causes of differences: NAV vs illiquid exchange trades: stale last-traded prices, wide intraday prints and days without trades.

- **GOLD** — expected causes of differences: Exchange close vs end-of-day NAV (timing, ETF premium/discount); NAV is split-adjusted here for comparison; Yahoo double-adjusted rows show as ~-99%.


The LTGILTBEES exchange series covers 92.20% of reference sessions (status `FAIL`). On matched dates its daily returns have correlation 0.338 with NAV returns and the standard deviation of daily return differences is 0.775%; 27 matched days differ from NAV by more than 1%. These figures are the basis for using AMFI NAV as the bond return series.


Risk-free cross-checks: overlapping Handbook editions are compared auction by auction, and every reported implicit yield is recomputed from the cut-off price (`(100/P - 1) x 365/91`).

Equities and NIFTY 50 have no independent secondary source (NSE inaccessible); only internal consistency checks apply.

## 9. Common-date coverage

- Common period: 2019-01-02 to 2025-12-31 — 1690 dates, 1689 returns.
- Reference sessions dropped from the common sample: 40.

| Dataset | Sessions absent | Dates |
|---|---|---|
| GSEC | 36 | 2019-02-19, 2019-04-01, 2019-10-27, 2020-02-19, 2020-03-25, 2020-04-01, 2020-05-07, 2020-10-30, 2020-11-14, 2021-02-19 … |
| GOLD | 3 | 2019-12-19, 2019-12-20, 2025-10-24 |
| NIFTY50 | 3 | 2019-01-01, 2019-10-27, 2020-11-14 |


38 aligned return(s) span more than one reference session because a date was dropped; they are listed in `processed/metadata/return_intervals.csv` (`sessions_spanned > 1`): 2019-02-20 (2), 2019-04-02 (2), 2019-10-29 (2), 2019-12-23 (3), 2020-02-20 (2), 2020-03-26 (2), 2020-04-03 (2), 2020-05-08 (2), 2020-11-02 (2), 2020-11-17 (2), 2021-02-22 (2), 2021-04-05 (2), 2021-04-15 (2), 2021-05-27 (2), 2021-08-17 (2), 2021-10-20 (2), 2021-11-08 (2), 2022-02-08 (2), 2022-04-04 (2), 2022-05-17 (2), 2022-08-17 (2), 2022-10-25 (2), 2023-03-23 (2), 2023-05-08 (2), 2023-08-17 (2), 2024-02-20 (2), 2024-04-02 (2), 2024-04-10 (2), 2024-05-24 (2), 2024-09-19 (2), 2024-11-04 (2), 2025-02-03 (2), 2025-02-20 (2), 2025-04-02 (2), 2025-05-13 (2), 2025-09-09 (2), 2025-10-23 (2), 2025-10-27 (2).


**Risk-free alignment (to be applied in Phase 3, not in this phase):** the weekly auction series is kept at native frequency in `processed/risk_free/RF_TBILL_91D.csv`. Proposed procedure: for each aligned return interval (t-1, t], use the most recent implicit yield whose *auction date* is on or before t-1 (backward as-of join on information available at the start of the interval) and accrue it over the interval's calendar days on the series' actual/365 basis: `rf_t = y/100 x days(t-1, t)/365`. Auctions from the month before the study start are retained for this lookup. This carries a published reference rate forward between auctions; it is not an observation of a daily market yield, and the convention must be approved before use.


Risk-free coverage: 360 auctions in the study period (2019-01-02 to 2025-12-24), first lookback auction 2018-12-05, median spacing 7.0 days, longest gap 22 days.

## 10. Known limitations

- GOLD: Records deviating from the split-adjusted AMFI NAV by more than the source-error threshold are excluded as source errors (not repaired).
- GSEC: Investors trading on NSE transact at market prices that can deviate from NAV.
- GSEC: NAV is used instead of the NSE price because LTGILTBEES exchange trading is too illiquid for daily returns (see GSEC_EXCHANGE cross-check).
- HDFCBANK: Adjusted-close levels are rescaled whenever later dividends occur, so absolute levels differ between download dates; daily returns are unaffected.
- HDFCBANK: No independent secondary source: NSE blocks automated access (HTTP 403).
- HINDUNILVR: Adjusted-close levels are rescaled whenever later dividends occur, so absolute levels differ between download dates; daily returns are unaffected.
- HINDUNILVR: No independent secondary source: NSE blocks automated access (HTTP 403).
- MM: Adjusted-close levels are rescaled whenever later dividends occur, so absolute levels differ between download dates; daily returns are unaffected.
- MM: No independent secondary source: NSE blocks automated access (HTTP 403).
- NIFTY50: Preferred source (NSE / NSE Indices) is not accessible to automated clients; Yahoo Finance is used instead.
- NIFTY50: Price index, not the NIFTY 50 Total Return Index: the benchmark excludes dividends while equity returns include them (adjusted close).
- RBI_HOLIDAYS_MUMBAI: Bank holidays are evidence for missing debt-fund NAVs, not an NSE trading calendar (NSE's own holiday circulars are not accessible to automated clients).
- RELIANCE: Adjusted-close levels are rescaled whenever later dividends occur, so absolute levels differ between download dates; daily returns are unaffected.
- RELIANCE: No independent secondary source: NSE blocks automated access (HTTP 403).
- RF_TBILL_91D: Each Handbook edition covers about one fiscal year; editions are combined.
- RF_TBILL_91D: Weekly primary-auction yields, not a daily secondary-market yield.
- SUNPHARMA: Adjusted-close levels are rescaled whenever later dividends occur, so absolute levels differ between download dates; daily returns are unaffected.
- SUNPHARMA: No independent secondary source: NSE blocks automated access (HTTP 403).
- TCS: Adjusted-close levels are rescaled whenever later dividends occur, so absolute levels differ between download dates; daily returns are unaffected.
- TCS: No independent secondary source: NSE blocks automated access (HTTP 403).

## 11. Unresolved issues and warnings

- MM: extreme_returns: 1 return(s) beyond +/-15% flagged for investigation (retained)
- GSEC: expected_non_valuation_days: 36 NSE session(s) without an observation on documented non-valuation days {'RBI Mumbai bank holiday': 33, 'weekend special NSE session': 3}; these dates drop out of the common sample
- GSEC: off_calendar_dates: 4 observation date(s) not in the reference NSE calendar (dropped by common-date alignment)
- GOLD: source_errors: 2 record(s) deviate >20% from GOLD_NAV and were excluded: 2019-12-19 (0.3355 vs ref 33.5323), 2019-12-20 (0.3365 vs ref 33.5864)
- GOLD: record_exclusions: Excluded records: {'source_error': 2}
- GOLD: session_coverage: 1727/1730 expected sessions (99.83%); missing 3
- NIFTY50: session_coverage: 1727/1730 expected sessions (99.83%); missing 3
- NIFTY50: extreme_returns: 1 return(s) beyond +/-10% flagged for investigation (retained)
- RF_TBILL_91D: record_exclusions: Excluded records: {'missing_value': 3}
- RF_TBILL_91D: auction_gaps: Longest gap 22 days; 5 gap(s) over 8 days
- RF_TBILL_91D: auctions_without_yield: No implicit yield published (e.g. all bids rejected): 2023-03-29, 2025-02-20
- GSEC_EXCHANGE: session_coverage: 1595/1730 expected sessions (92.20%); missing 135
- GSEC_EXCHANGE: longest_gap: Longest run of missing sessions: 109 (from 2019-01-07)
- GSEC_EXCHANGE: extreme_returns: 8 return(s) beyond +/-3% flagged for investigation (retained)
- GOLD_NAV: expected_non_valuation_days: 6 NSE session(s) without an observation on documented non-valuation days {'weekend special NSE session': 2, 'RBI Mumbai bank holiday': 4}; these dates drop out of the common sample
- GOLD_NAV: off_calendar_dates: 5 observation date(s) not in the reference NSE calendar (dropped by common-date alignment)
- GOLD_NAV: extreme_returns: 1 return(s) beyond +/-6% flagged for investigation (retained)
- alignment: 38 aligned return(s) span more than one reference session because a date was missing in at least one series
- calendar: probable NSE sessions absent from every Yahoo series: 2019-02-13, 2019-03-29


Decisions requiring approval:

1. Use AMFI NAV (not the illiquid NSE price) for the government-bond ETF.
2. Exclude, rather than repair, the Yahoo GOLDBEES records flagged as source errors.
3. Use the NIFTY 50 price index (no Total Return Index available from an accessible source).
4. Use weekly 91-day T-bill primary-auction yields with the as-of procedure in §9.
5. Treat missing NAVs on RBI Mumbai holidays and weekend special sessions as non-valuation days (dropped from the common sample, never filled).

## 12. Readiness for Phase 3

**PASS_WITH_WARNINGS.** The validated dataset can be used in Phase 3, subject to the limitations and approval items above.


119 checks run: 2 failed, 15 warned. Cross-check datasets (GSEC_EXCHANGE, GOLD_NAV) are never used as analysis inputs.
