"""Human-readable data-quality report (data/reports/data_quality_report.md).

All figures are taken from the pipeline result; the prose explains the decisions
encoded in the source registry and cleaning rules.
"""

from typing import Any

from app.data_pipeline import PIPELINE_VERSION
from app.data_pipeline.pipeline import PipelineResult
from app.data_pipeline.quality_checks import CheckStatus, OverallStatus
from app.data_pipeline.reporting import alignment_summary, coverage_rows
from app.data_pipeline.source_registry import DatasetRole


def _pct(x: Any, digits: int = 2) -> str:
    return "n/a" if x is None else f"{x * 100:.{digits}f}%"


def _v(x: Any) -> str:
    return "n/a" if x is None or x == "" else str(x)


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(_v(c).replace("|", "/") for c in row) + " |" for row in rows]
    return "\n".join(out)


def render_report(result: PipelineResult, summary: dict[str, Any]) -> str:
    ds = result.datasets
    align = alignment_summary(result)
    common = align.get("common_period") or {}
    parts: list[str] = []
    add = parts.append

    add("# Data-quality report — Phase 2\n")
    add(
        f"Generated {result.generated_at.isoformat()} by pipeline v{PIPELINE_VERSION}. "
        "This file is regenerated on every run; do not edit by hand.\n"
    )

    # 1 ------------------------------------------------------------------------
    add("## 1. Executive summary\n")
    add(
        f"**Overall status: `{result.overall.value}`** — ready for Phase 3: **{'yes' if result.ready else 'no'}**.\n"
    )
    add(
        f"- Requested study period: {result.study_start} to {result.study_end}.\n"
        f"- Common sample (8 assets + NIFTY 50): {_v(common.get('first'))} to {_v(common.get('last'))}, "
        f"{_v(common.get('price_dates'))} price dates / {_v(common.get('return_observations'))} daily returns "
        f"({_pct(common.get('session_coverage'))} of reference sessions).\n"
        f"- Critical failures: {len(result.critical_failures)}; warnings: {len(result.warnings)}; "
        f"documented limitations: {len(result.limitations)}.\n"
    )
    if result.critical_failures:
        add("Critical failures:\n")
        add("\n".join(f"- {m}" for m in result.critical_failures) + "\n")

    # 2 ------------------------------------------------------------------------
    add("## 2. Sources used\n")
    rows = []
    for d in ds.values():
        rows.append(
            [
                d.spec.dataset_id,
                d.spec.role.value,
                d.spec.source.source_name,
                d.spec.source.value_field,
                d.retrieval_status,
                d.snapshot.retrieved_at.isoformat() if d.snapshot else "—",
            ]
        )
    add(
        _table(
            ["Dataset", "Role", "Source", "Selected field", "Retrieval", "Retrieved (UTC)"], rows
        )
        + "\n"
    )
    add(
        "Source decisions:\n\n"
        "- **Equities** — Yahoo Finance via `yfinance` (`Adj Close`, split- and dividend-adjusted). "
        "NSE was the planned cross-check but rejects automated clients (HTTP 403), so no "
        "independent equity source was available.\n"
        "- **NIFTY 50** — Yahoo Finance `^NSEI` (price index). NSE / NSE Indices historical "
        "endpoints are not accessible to automated clients.\n"
        "- **Government bonds** — AMFI daily NAV of the LTGILTBEES ETF. The NSE exchange price "
        "(Yahoo `LTGILTBEES.NS`) was retrieved and rejected as the return series because the ETF "
        "is thinly traded (see §8 and the `GSEC_EXCHANGE` row). This is the same instrument, not a "
        "substitution.\n"
        "- **Gold** — Yahoo Finance `GOLDBEES.NS` exchange price, cross-checked against AMFI NAV.\n"
        "- **Risk-free rate** — RBI *Handbook of Statistics on Indian Economy*, table "
        "'Auctions of 91-Day Government of India Treasury Bills', one HTML table per annual "
        "edition on www.rbi.org.in. DBIE has no public API and rbidocs.rbi.org.in file downloads "
        "are behind a CAPTCHA, so the Handbook tables (the same RBI data) are used.\n"
    )

    # 3 ------------------------------------------------------------------------
    add("## 3. Identifiers verified\n")
    rows = []
    for d in ds.values():
        ident = next((c for c in d.quality.checks if c.name == "identity"), None)
        rows.append(
            [
                d.spec.dataset_id,
                d.spec.name,
                d.spec.source.identifier,
                ", ".join(
                    f"{k}={v}" for k, v in d.spec.source.params.items() if k != "edition_years"
                )
                or "—",
                f"{ident.status.value}: {ident.detail}" if ident else "not checked",
            ]
        )
    add(
        _table(["Dataset", "Instrument", "Identifier", "Other identifiers", "Identity check"], rows)
        + "\n"
    )

    # 4 ------------------------------------------------------------------------
    add("## 4. Date coverage by instrument\n")
    rows = [
        [
            r["dataset_id"],
            r["earliest_date"],
            r["latest_date"],
            r["observations"],
            r["missing_sessions"],
            _pct(r["target_period_coverage"]),
            r["covers_target_period"],
            r["validation_status"],
        ]
        for r in coverage_rows(result)
    ]
    add(
        _table(
            [
                "Dataset",
                "First",
                "Last",
                "Obs.",
                "Missing sessions",
                "Session coverage",
                "Covers period",
                "Status",
            ],
            rows,
        )
        + "\n"
    )
    add(
        "Session coverage is measured against the reference NSE calendar: the union of trading "
        f"dates in the six equity series ({len(result.calendar)} sessions, including special "
        "Muhurat sessions). The risk-free series is weekly and is measured by auction cadence instead.\n"
    )

    # 5 ------------------------------------------------------------------------
    add("## 5. Data-cleaning decisions\n")
    add(
        "- Dates are normalized to timezone-naive exchange-local (Asia/Kolkata) dates; original "
        "timestamps are kept in `source_timestamp`.\n"
        "- Values are parsed without coercion: explicit missing markers (`-`, `N.A.`, empty) and "
        "non-numeric text are flagged, not converted.\n"
        "- Records are **flagged then excluded** for: invalid date, missing value, non-numeric, "
        "non-finite, non-positive price (or yield outside "
        "0–20%), conflicting duplicate dates, and source errors (gold only: deviation >20% from "
        "split-adjusted NAV). Identical duplicates keep one record. For the risk-free series, "
        "overlapping Handbook editions keep the latest edition.\n"
        "- No forward-filling, interpolation or zero-filled returns. Extreme returns are flagged "
        "and retained.\n"
        "- Daily simple returns `r_t = P_t / P_(t-1) - 1` are computed from cleaned series; nothing "
        "is annualized in this phase. Yields are never passed through the return formula.\n"
    )
    add("Excluded records (all are listed in `excluded_records.csv`):\n")
    rows = [
        [
            d.spec.dataset_id,
            d.quality.missing.get("excluded_total"),
            d.quality.missing.get("excluded_by_reason"),
        ]
        for d in ds.values()
        if d.quality.missing.get("excluded_total")
    ]
    add((_table(["Dataset", "Excluded", "By reason"], rows) if rows else "None.") + "\n")

    # 6 ------------------------------------------------------------------------
    add("## 6. Missing values and gaps\n")
    rows = []
    for d in ds.values():
        c, m = d.quality.coverage, d.quality.missing
        missing_dates = c.get("missing_session_dates") or []
        shown = ", ".join(missing_dates[:12]) + (
            f" … (+{len(missing_dates) - 12})" if len(missing_dates) > 12 else ""
        )
        rows.append(
            [
                d.spec.dataset_id,
                m.get("missing_value"),
                c.get("sessions_missing", "—"),
                c.get("sessions_not_expected", "—"),
                c.get("longest_missing_session_run", "—"),
                c.get("longest_calendar_gap_days"),
                shown or "—",
            ]
        )
    add(
        _table(
            [
                "Dataset",
                "Missing values (raw)",
                "Missing sessions (unexplained)",
                "Non-valuation days (explained)",
                "Longest missing run",
                "Longest gap (days)",
                "Missing session dates",
            ],
            rows,
        )
        + "\n"
    )
    add(
        "\n**Non-valuation days (AMFI NAV series only).** AMFI does not publish a NAV on days "
        "that are not fund business days. A missing NAV on an NSE session is classified as "
        "*explained* only if the date is (a) a weekend special NSE session (Muhurat / Budget-day "
        "trading) or (b) listed in RBI's official Mumbai holiday matrix (`RBI_HOLIDAYS_MUMBAI`), "
        "when the government-securities market is closed. Explained dates are excluded from the "
        "coverage ratio but are **not filled**: they drop out of the common sample. Any other "
        "missing date counts against coverage.\n"
    )
    probable = result.calendar_findings.get("probable_missing_sessions", [])
    add(
        "\n**Reference-calendar gaps.** The reference calendar is built from the Yahoo equity "
        "series, so a session missing from *every* Yahoo series is invisible to per-series "
        "checks. Weekdays that are not RBI Mumbai holidays but on which AMFI struck a NAV are "
        f"reported as probable NSE sessions missing from Yahoo: {', '.join(probable) or 'none'}. "
        "On these dates no equity, index or gold price exists in the source, so the following "
        "return in every series spans two sessions (not reflected in `sessions_spanned`, which "
        "uses the Yahoo-derived calendar).\n"
    )

    # 7 ------------------------------------------------------------------------
    add("## 7. Corporate-action considerations\n")
    add(
        "- Equities use Yahoo `Adj Close`, which back-adjusts for splits, bonus issues and cash "
        "dividends. No manual adjustments are applied on top. Split/bonus events in the period "
        "(HDFC Bank 2019 and 2025, Reliance 2024) are covered by the automated discontinuity "
        "check (any daily return beyond +/-50% fails). The Reliance -> Jio Financial demerger "
        "(ex-date 2023-07-20) is too small for that check and was inspected manually during "
        "source verification: the Yahoo series shows -0.12% on 2023-07-20, i.e. the spin-off "
        "value is already reflected in the adjusted history.\n"
        "- Adjusted-close levels depend on the download date (later dividends rescale history); "
        "returns do not. The raw snapshot is reused on later runs for reproducibility.\n"
        "- Gold BeES: 1:100 unit split, exchange ex-date 2019-12-19; AMFI NAV per unit changes "
        "from 2019-12-23. Yahoo's back-adjusted series is used as delivered; the NAV is divided by "
        "100 before 2019-12-23 **only for the cross-check**.\n"
        "- The G-Sec ETF and gold ETF are growth ETFs with no distributions in the period; "
        "NIFTY 50 is a price index (dividends excluded).\n"
    )

    # 8 ------------------------------------------------------------------------
    add("## 8. Cross-source checks\n")
    if result.cross_checks:
        rows = [
            [
                c["dataset_id"],
                c["reference_dataset_id"],
                c["matched_dates"],
                _pct(c["median_abs_level_deviation"], 3),
                _pct(c["p95_abs_level_deviation"], 3),
                f"{_pct(c['max_abs_level_deviation'], 1)} ({c['max_deviation_date']})",
                c["days_over_5pct"],
                _v(
                    round(c["return_correlation"], 4)
                    if c["return_correlation"] is not None
                    else None
                ),
                c["excluded_source_errors"],
            ]
            for c in result.cross_checks
        ]
        add(
            _table(
                [
                    "Primary",
                    "Reference",
                    "Matched dates",
                    "Median abs dev",
                    "P95 abs dev",
                    "Max abs dev",
                    "Days >5%",
                    "Return corr.",
                    "Excluded source errors",
                ],
                rows,
            )
            + "\n"
        )
        for c in result.cross_checks:
            add(
                f"- **{c['dataset_id']}** — expected causes of differences: {c['expected_causes']}\n"
            )
    else:
        add("No cross-source comparison could be run.\n")
    ex = ds.get("GSEC_EXCHANGE")
    gsec = next((c for c in result.cross_checks if c["dataset_id"] == "GSEC"), None)
    if ex is not None and ex.quality.coverage and gsec is not None:
        add(
            f"\nThe LTGILTBEES exchange series covers {_pct(ex.quality.coverage.get('session_coverage'))} "
            f"of reference sessions (status `{ex.status.value}`). On matched dates its daily returns "
            f"have correlation {gsec['return_correlation']:.3f} with NAV returns and the standard "
            f"deviation of daily return differences is {_pct(gsec['return_difference_std'], 3)}; "
            f"{gsec['days_over_1pct']} matched days differ from NAV by more than 1%. These figures are "
            "the basis for using AMFI NAV as the bond return series.\n"
        )
    add(
        "\nRisk-free cross-checks: overlapping Handbook editions are compared auction by auction, and "
        "every reported implicit yield is recomputed from the cut-off price "
        "(`(100/P - 1) x 365/91`).\n"
    )
    add(
        "Equities and NIFTY 50 have no independent secondary source (NSE inaccessible); only internal consistency checks apply.\n"
    )

    # 9 ------------------------------------------------------------------------
    add("## 9. Common-date coverage\n")
    if align.get("status") == "not_aligned":
        add(f"Alignment was not performed: {align.get('error')}\n")
    else:
        dropped = align.get("sessions_dropped_by_dataset", {})
        add(
            f"- Common period: {common.get('first')} to {common.get('last')} — {common.get('price_dates')} "
            f"dates, {common.get('return_observations')} returns.\n"
            f"- Reference sessions dropped from the common sample: {len(align.get('sessions_dropped', []))}.\n"
        )
        rows = [
            [k, len(v), ", ".join(v[:10]) + (" …" if len(v) > 10 else "")]
            for k, v in dropped.items()
        ]
        if rows:
            add(_table(["Dataset", "Sessions absent", "Dates"], rows) + "\n")
        multi = align.get("multi_session_returns", {})
        add(
            f"\n{len(multi)} aligned return(s) span more than one reference session because a date "
            "was dropped; they are listed in `processed/metadata/return_intervals.csv` "
            f"(`sessions_spanned > 1`): {', '.join(f'{d} ({n})' for d, n in multi.items()) or 'none'}.\n"
        )
    rf = ds.get("RF_TBILL_91D")
    add(
        "\n**Risk-free alignment (to be applied in Phase 3, not in this phase):** the weekly "
        "auction series is kept at native frequency in `processed/risk_free/RF_TBILL_91D.csv`. "
        "Proposed procedure: for each aligned return interval (t-1, t], use the most recent "
        "implicit yield whose *auction date* is on or before t-1 (backward as-of join on "
        "information available at the start of the interval) and accrue it over the interval's "
        "calendar days on the series' actual/365 basis: `rf_t = y/100 x days(t-1, t)/365`. "
        "Auctions from the month before the study start are retained for this lookup. This "
        "carries a published reference rate forward between auctions; it is not an observation "
        "of a daily market yield, and the convention must be approved before use.\n"
    )
    if rf is not None and rf.quality.coverage:
        c = rf.quality.coverage
        add(
            f"\nRisk-free coverage: {c.get('observations')} auctions in the study period "
            f"({c.get('first_date')} to {c.get('last_date')}), first lookback auction "
            f"{c.get('first_lookback_date')}, median spacing {c.get('median_gap_days')} days, longest gap "
            f"{c.get('longest_calendar_gap_days')} days.\n"
        )

    # 10 -----------------------------------------------------------------------
    add("## 10. Known limitations\n")
    add("\n".join(f"- {m}" for m in result.limitations) + "\n")

    # 11 -----------------------------------------------------------------------
    add("## 11. Unresolved issues and warnings\n")
    add(("\n".join(f"- {m}" for m in result.warnings) if result.warnings else "None.") + "\n")
    add(
        "\nDecisions requiring approval:\n\n"
        "1. Use AMFI NAV (not the illiquid NSE price) for the government-bond ETF.\n"
        "2. Exclude, rather than repair, the Yahoo GOLDBEES records flagged as source errors.\n"
        "3. Use the NIFTY 50 price index (no Total Return Index available from an accessible source).\n"
        "4. Use weekly 91-day T-bill primary-auction yields with the as-of procedure in §9.\n"
        "5. Treat missing NAVs on RBI Mumbai holidays and weekend special sessions as "
        "non-valuation days (dropped from the common sample, never filled).\n"
    )

    # 12 -----------------------------------------------------------------------
    add("## 12. Readiness for Phase 3\n")
    if result.overall is OverallStatus.BLOCKED:
        add(
            "**BLOCKED.** Downstream analytics must not run until the critical failures above are resolved.\n"
        )
    else:
        add(
            f"**{result.overall.value}.** The validated dataset can be used in Phase 3, subject to the "
            "limitations and approval items above.\n"
        )
    checks = sum(len(d.quality.checks) for d in ds.values())
    fails = sum(1 for d in ds.values() for c in d.quality.checks if c.status is CheckStatus.FAIL)
    warns = sum(1 for d in ds.values() for c in d.quality.checks if c.status is CheckStatus.WARN)
    roles = {d.spec.dataset_id: d.spec.role for d in ds.values()}
    add(
        f"\n{checks} checks run: {fails} failed, {warns} warned. Cross-check datasets "
        f"({', '.join(k for k, r in roles.items() if r is DatasetRole.CROSS_CHECK)}) are never "
        "used as analysis inputs.\n"
    )
    return "\n".join(parts)
