"""Dataset-level validation checks and status calculation.

A check yields ``pass``, ``warn`` or ``fail``. A dataset FAILS if any check fails,
is PASS_WITH_WARNINGS if any check warns, and PASS otherwise. Extreme returns are
flagged for investigation and kept; only discontinuities beyond the threshold fail.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd

from app.data_pipeline.config import QualityThresholds
from app.data_pipeline.raw_store import RawSnapshot
from app.data_pipeline.returns import sessions_spanned, simple_returns
from app.data_pipeline.source_registry import DatasetSpec, SourceKind


class CheckStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DatasetStatus(StrEnum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"
    NOT_RETRIEVED = "NOT_RETRIEVED"


class OverallStatus(StrEnum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str
    value: Any = None


@dataclass
class DatasetQuality:
    dataset_id: str
    checks: list[CheckResult] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    missing: dict[str, Any] = field(default_factory=dict)
    extreme_returns: pd.DataFrame | None = None
    retrieved: bool = True

    def add(self, name: str, status: CheckStatus, detail: str, value: Any = None) -> None:
        self.checks.append(CheckResult(name, status, detail, value))

    @property
    def status(self) -> DatasetStatus:
        if not self.retrieved:
            return DatasetStatus.NOT_RETRIEVED
        statuses = {c.status for c in self.checks}
        if CheckStatus.FAIL in statuses:
            return DatasetStatus.FAIL
        if CheckStatus.WARN in statuses:
            return DatasetStatus.PASS_WITH_WARNINGS
        return DatasetStatus.PASS

    def messages(self, status: CheckStatus) -> list[str]:
        return [f"{c.name}: {c.detail}" for c in self.checks if c.status is status]


def dataset_status_from(checks: list[CheckStatus]) -> DatasetStatus:
    if CheckStatus.FAIL in checks:
        return DatasetStatus.FAIL
    if CheckStatus.WARN in checks:
        return DatasetStatus.PASS_WITH_WARNINGS
    return DatasetStatus.PASS


def overall_status(
    statuses: dict[str, DatasetStatus],
    critical: set[str],
    *,
    alignment_ok: bool,
    has_warnings: bool,
) -> OverallStatus:
    blocked = any(
        statuses.get(d) in (DatasetStatus.FAIL, DatasetStatus.NOT_RETRIEVED, None) for d in critical
    )
    if blocked or not alignment_ok:
        return OverallStatus.BLOCKED
    if has_warnings or any(s is not DatasetStatus.PASS for s in statuses.values()):
        return OverallStatus.PASS_WITH_WARNINGS
    return OverallStatus.PASS


# --------------------------------------------------------------------------------
# Identity


def _norm(text: str) -> str:
    return " ".join(str(text).casefold().split())


def check_identity(
    q: DatasetQuality, spec: DatasetSpec, snapshot: RawSnapshot, df: pd.DataFrame
) -> None:
    expected = _norm(spec.source.expected_name)
    kind = spec.source.kind
    if kind is SourceKind.YAHOO:
        meta = snapshot.source_metadata
        names = [_norm(meta.get(k, "")) for k in ("longName", "shortName")]
        symbol_ok = meta.get("symbol") in (None, spec.source.identifier)
        if any(expected in n for n in names if n) and symbol_ok:
            q.add("identity", CheckStatus.PASS, f"Source reports {meta.get('longName')!r}")
        elif not any(names):
            q.add("identity", CheckStatus.WARN, "Source metadata has no instrument name")
        else:
            q.add(
                "identity", CheckStatus.FAIL, f"Source name {meta.get('longName')!r} does not match"
            )
        currency = meta.get("currency")
        if spec.currency and currency != spec.currency:
            q.add(
                "currency", CheckStatus.FAIL, f"Expected {spec.currency}, source reports {currency}"
            )
        else:
            q.add("currency", CheckStatus.PASS, f"{currency}")
    elif kind is SourceKind.AMFI_NAV:
        names = set(df["scheme_name"].map(_norm))
        isins = set(df["isin"])
        expected_isin = spec.source.params.get("isin")
        if names == {expected} and isins == {expected_isin}:
            q.add(
                "identity",
                CheckStatus.PASS,
                f"Scheme {spec.source.identifier}, ISIN {expected_isin}",
            )
        else:
            q.add("identity", CheckStatus.FAIL, f"Unexpected scheme names {names} / ISINs {isins}")
    elif kind is SourceKind.RBI_HOLIDAYS:
        pages = [f.content.decode("utf-8") for f in snapshot.files]
        ok = all(spec.source.expected_name in p for p in pages)
        q.add(
            "identity",
            CheckStatus.PASS if ok else CheckStatus.FAIL,
            f"{len(pages)} yearly page(s) for '{spec.source.expected_name}'",
        )
    elif kind is SourceKind.RBI_HANDBOOK:
        pages = [f.content.decode("utf-8") for f in snapshot.files]
        ok = all(
            spec.source.expected_name in p and "Implicit Yield at Cut-off Price (per" in p
            for p in pages
        )
        q.add(
            "identity",
            CheckStatus.PASS if ok else CheckStatus.FAIL,
            f"{len(pages)} edition page(s) titled '{spec.source.expected_name}'",
        )


# --------------------------------------------------------------------------------
# Records


def summarize_records(q: DatasetQuality, df: pd.DataFrame) -> None:
    reasons = df.loc[df["excluded"], "exclusion_reason"].value_counts().to_dict()
    total = len(df)
    q.missing = {
        "records": total,
        "missing_value": int(df["is_missing"].sum()),
        "missing_value_pct": float(df["is_missing"].mean() * 100) if total else 0.0,
        "non_numeric": int(df["is_non_numeric"].sum()),
        "non_finite": int(df["is_non_finite"].sum()),
        "invalid_date": int(df["is_invalid_date"].sum()),
        "duplicate_dates": int(df.loc[df["date"].notna(), "date"].duplicated().sum()),
        "excluded_by_reason": {str(k): int(v) for k, v in reasons.items()},
        "excluded_total": int(df["excluded"].sum()),
        "valid_records": int((~df["excluded"]).sum()),
    }
    benign = {"duplicate_identical"}
    serious = {k: v for k, v in reasons.items() if k not in benign}
    if serious:
        q.add("record_exclusions", CheckStatus.WARN, f"Excluded records: {serious}", serious)
    else:
        q.add("record_exclusions", CheckStatus.PASS, "No invalid records excluded")
    conflicts = reasons.get("duplicate_conflict", 0)
    dup_status = CheckStatus.WARN if conflicts else CheckStatus.PASS
    q.add(
        "duplicate_dates",
        dup_status,
        f"{q.missing['duplicate_dates']} repeated date(s), {conflicts} conflicting",
    )


# --------------------------------------------------------------------------------
# Daily coverage


def _longest_run(missing: pd.DatetimeIndex, calendar: pd.DatetimeIndex) -> tuple[int, str | None]:
    if len(missing) == 0:
        return 0, None
    pos = np.sort(calendar.get_indexer(missing))
    best, best_start, run, start = 1, pos[0], 1, pos[0]
    for prev, cur in pairwise(pos):
        run = run + 1 if cur == prev + 1 else 1
        start = start if cur == prev + 1 else cur
        if run > best:
            best, best_start = run, start
    return int(best), calendar[best_start].date().isoformat()


def check_daily_coverage(
    q: DatasetQuality,
    series: pd.Series,
    calendar: pd.DatetimeIndex,
    study_start: date,
    study_end: date,
    t: QualityThresholds,
    explained: dict[pd.Timestamp, str] | None = None,
) -> None:
    """Coverage against the reference calendar.

    ``explained`` maps sessions on which the instrument is *expected* to have no
    observation (e.g. no NAV is struck on a bank holiday) to the documented reason.
    Explained sessions are reported but excluded from the coverage ratio and gap
    checks; everything else counts as missing data.
    """
    explained = explained or {}
    in_period = series[
        (series.index >= pd.Timestamp(study_start)) & (series.index <= pd.Timestamp(study_end))
    ]
    idx = pd.DatetimeIndex(in_period.index)
    q.coverage.update(
        {
            "requested_start": study_start.isoformat(),
            "requested_end": study_end.isoformat(),
            "first_date": idx.min().date().isoformat() if len(idx) else None,
            "last_date": idx.max().date().isoformat() if len(idx) else None,
            "observations": len(idx),
            "unique_dates": int(idx.nunique()),
        }
    )
    if len(idx) == 0 or len(calendar) == 0:
        q.add("coverage", CheckStatus.FAIL, "No valid observations in the study period")
        return

    present = idx.intersection(calendar)
    all_missing = calendar.difference(idx)
    explained_missing = pd.DatetimeIndex([d for d in all_missing if d in explained])
    missing = all_missing.difference(explained_missing)
    expected = calendar.difference(explained_missing)
    extra = idx.difference(calendar)
    ratio = len(present) / len(expected)
    longest, longest_start = _longest_run(missing, calendar)
    gaps = pd.Series(idx[1:] - idx[:-1]).dt.days
    q.coverage.update(
        {
            "reference_sessions": len(calendar),
            "sessions_present": len(present),
            "sessions_missing": len(missing),
            "missing_session_dates": [d.date().isoformat() for d in missing],
            "sessions_not_expected": len(explained_missing),
            "sessions_not_expected_detail": {
                d.date().isoformat(): explained[d] for d in explained_missing
            },
            "raw_session_coverage": len(present) / len(calendar),
            "dates_outside_reference_calendar": [d.date().isoformat() for d in extra],
            "session_coverage": ratio,
            "longest_missing_session_run": longest,
            "longest_missing_run_start": longest_start,
            "longest_calendar_gap_days": int(gaps.max()) if len(gaps) else 0,
        }
    )
    q.missing["missing_sessions"] = len(missing)
    q.missing["missing_sessions_pct"] = (1 - ratio) * 100

    tol = pd.Timedelta(days=t.boundary_tolerance_days)
    starts_ok = idx.min() <= calendar[0] + tol
    ends_ok = idx.max() >= calendar[-1] - tol
    q.coverage["covers_target_period"] = bool(starts_ok and ends_ok)
    q.add(
        "period_boundaries",
        CheckStatus.PASS if starts_ok and ends_ok else CheckStatus.FAIL,
        f"{q.coverage['first_date']} .. {q.coverage['last_date']} vs sessions "
        f"{calendar[0].date()} .. {calendar[-1].date()}",
    )
    if ratio < t.min_session_coverage:
        status = CheckStatus.FAIL
    elif len(missing):
        status = CheckStatus.WARN
    else:
        status = CheckStatus.PASS
    q.add(
        "session_coverage",
        status,
        f"{len(present)}/{len(expected)} expected sessions ({ratio:.2%}); missing {len(missing)}",
        ratio,
    )
    if len(explained_missing):
        reasons: dict[str, int] = {}
        for d in explained_missing:
            key = explained[d].split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1
        q.add(
            "expected_non_valuation_days",
            CheckStatus.WARN,
            f"{len(explained_missing)} NSE session(s) without an observation on documented "
            f"non-valuation days {reasons}; these dates drop out of the common sample",
            len(explained_missing),
        )
    run_status = CheckStatus.FAIL if longest > t.max_missing_session_run else CheckStatus.PASS
    q.add(
        "longest_gap",
        run_status,
        f"Longest run of missing sessions: {longest} (from {longest_start})",
        longest,
    )
    if len(extra):
        q.add(
            "off_calendar_dates",
            CheckStatus.WARN,
            f"{len(extra)} observation date(s) not in the reference NSE calendar "
            "(dropped by common-date alignment)",
        )


def check_returns(
    q: DatasetQuality,
    spec: DatasetSpec,
    series: pd.Series,
    calendar: pd.DatetimeIndex,
    t: QualityThresholds,
) -> pd.DataFrame:
    """Native returns over consecutive valid observations, with anomaly flags."""
    if len(series) < 2:
        return pd.DataFrame(columns=["simple_return", "sessions_spanned"])
    rets = simple_returns(series.sort_index())
    spans = sessions_spanned(pd.DatetimeIndex(series.sort_index().index), calendar)
    out = pd.DataFrame({"simple_return": rets, "sessions_spanned": spans.reindex(rets.index)})
    out.index.name = "date"

    disc = out[out["simple_return"].abs() > t.discontinuity_return]
    if len(disc):
        q.add(
            "discontinuities",
            CheckStatus.FAIL,
            f"{len(disc)} return(s) beyond +/-{t.discontinuity_return:.0%}: "
            + ", ".join(f"{d.date()} {r:+.2%}" for d, r in disc["simple_return"].items()),
        )
    else:
        q.add(
            "discontinuities", CheckStatus.PASS, f"No return beyond +/-{t.discontinuity_return:.0%}"
        )

    threshold = spec.extreme_return_threshold
    if threshold is not None:
        ext = out[out["simple_return"].abs() > threshold].copy()
        prev = series.sort_index().shift(1).reindex(ext.index)
        ext["previous_value"] = prev
        ext["value"] = series.reindex(ext.index)
        ext["threshold"] = threshold
        q.extreme_returns = ext
        if len(ext):
            q.add(
                "extreme_returns",
                CheckStatus.WARN,
                f"{len(ext)} return(s) beyond +/-{threshold:.0%} flagged for "
                "investigation (retained)",
                len(ext),
            )
        else:
            q.add("extreme_returns", CheckStatus.PASS, f"None beyond +/-{threshold:.0%}")
    return out


def check_calendar_reference(
    q: DatasetQuality, df: pd.DataFrame, study_start: date, study_end: date
) -> None:
    valid = df[~df["excluded"]]
    per_year = valid.groupby(valid["date"].dt.year).size()
    years = range(study_start.year, study_end.year + 1)
    counts = {y: int(per_year.get(y, 0)) for y in years}
    q.coverage.update(
        {
            "first_date": _iso_or_none(valid["date"].min()),
            "last_date": _iso_or_none(valid["date"].max()),
            "observations": len(valid),
            "unique_dates": int(valid["date"].nunique()),
            "holidays_per_year": counts,
        }
    )
    thin = {y: c for y, c in counts.items() if c < 10}
    q.add(
        "coverage",
        CheckStatus.FAIL if thin else CheckStatus.PASS,
        f"Holidays per year {counts}" + (f"; implausibly few in {thin}" if thin else ""),
    )


def _iso_or_none(ts: object) -> str | None:
    return None if ts is None or pd.isna(ts) else pd.Timestamp(ts).date().isoformat()


# --------------------------------------------------------------------------------
# Risk-free (auction) series


def implied_yield_pct(price: pd.Series, tenor_days: int, basis: int) -> pd.Series:
    """Implicit yield of a discount bill: (100 / P - 1) * basis / tenor, in percent."""
    return (100.0 / price - 1.0) * basis / tenor_days * 100.0


def check_risk_free(
    q: DatasetQuality,
    df: pd.DataFrame,
    study_start: date,
    study_end: date,
    t: QualityThresholds,
) -> pd.DataFrame:
    """Validate the auction series; return the in-scope valid records."""
    lookback_start = pd.Timestamp(study_start) - pd.Timedelta(days=t.rf_lookback_days)
    valid = df[~df["excluded"]]
    scope = valid[(valid["date"] >= lookback_start) & (valid["date"] <= pd.Timestamp(study_end))]
    scope = scope.sort_values("date")
    dates = pd.DatetimeIndex(scope["date"])
    in_period = dates[dates >= pd.Timestamp(study_start)]
    gaps = pd.Series(dates[1:] - dates[:-1], index=dates[1:]).dt.days
    q.coverage.update(
        {
            "requested_start": study_start.isoformat(),
            "requested_end": study_end.isoformat(),
            "lookback_start": lookback_start.date().isoformat(),
            "first_date": in_period.min().date().isoformat() if len(in_period) else None,
            "last_date": in_period.max().date().isoformat() if len(in_period) else None,
            "first_lookback_date": dates.min().date().isoformat() if len(dates) else None,
            "observations": len(in_period),
            "unique_dates": int(in_period.nunique()),
            "median_gap_days": float(gaps.median()) if len(gaps) else None,
            "longest_calendar_gap_days": int(gaps.max()) if len(gaps) else None,
            "gaps_over_warning": {
                d.date().isoformat(): int(g) for d, g in gaps[gaps > t.rf_gap_warning_days].items()
            },
        }
    )
    if not len(in_period):
        q.add("coverage", CheckStatus.FAIL, "No auctions in the study period")
        return scope

    # As-of alignment needs an observation on or before the first study date.
    has_lookback = dates.min() <= pd.Timestamp(study_start)
    ends_ok = in_period.max() >= pd.Timestamp(study_end) - pd.Timedelta(days=t.rf_gap_warning_days)
    q.coverage["covers_target_period"] = bool(has_lookback and ends_ok)
    q.add(
        "period_boundaries",
        CheckStatus.PASS if has_lookback and ends_ok else CheckStatus.FAIL,
        f"Auctions {dates.min().date()} .. {in_period.max().date()} "
        f"(needs one on/before {study_start} and through {study_end})",
    )

    median_gap = gaps.median()
    weekly = 6 <= median_gap <= 8
    q.add(
        "frequency",
        CheckStatus.PASS if weekly else CheckStatus.FAIL,
        f"Median gap between auctions {median_gap:.0f} days (expected weekly)",
        float(median_gap),
    )
    worst = int(gaps.max())
    if worst > t.rf_gap_failure_days:
        gap_status = CheckStatus.FAIL
    elif worst > t.rf_gap_warning_days:
        gap_status = CheckStatus.WARN
    else:
        gap_status = CheckStatus.PASS
    q.add(
        "auction_gaps",
        gap_status,
        f"Longest gap {worst} days; {int((gaps > t.rf_gap_warning_days).sum())} gap(s) over "
        f"{t.rf_gap_warning_days} days",
        worst,
    )

    median_yield = float(scope["value"].median())
    units_ok = 1.0 <= median_yield <= 15.0
    q.add(
        "units",
        CheckStatus.PASS if units_ok else CheckStatus.FAIL,
        f"Median value {median_yield:.4f}: consistent with an annual yield in percent"
        if units_ok
        else f"Median value {median_yield} is not a percent yield (price or decimal?)",
    )

    implied = implied_yield_pct(scope["cut_off_price"], t.rf_tenor_days, t.rf_day_count_basis)
    diff = (scope["value"] - implied).abs()
    over = diff > t.rf_price_yield_tolerance_pp
    q.coverage["max_price_yield_diff_pp"] = float(diff.max()) if diff.notna().any() else None
    if diff.isna().all():
        q.add("price_yield_consistency", CheckStatus.WARN, "No cut-off prices to cross-check")
    elif (diff > 10 * t.rf_price_yield_tolerance_pp).any():
        q.add("price_yield_consistency", CheckStatus.FAIL, f"Max deviation {diff.max():.3f} pp")
    else:
        q.add(
            "price_yield_consistency",
            CheckStatus.WARN if over.any() else CheckStatus.PASS,
            f"Reported vs price-implied yield: max {diff.max():.4f} pp, "
            f"{int(over.sum())} above {t.rf_price_yield_tolerance_pp} pp",
        )

    no_yield = df[(df["exclusion_reason"] == "missing_value")]
    no_yield = no_yield[
        (no_yield["date"] >= lookback_start) & (no_yield["date"] <= pd.Timestamp(study_end))
    ]
    if len(no_yield):
        q.add(
            "auctions_without_yield",
            CheckStatus.WARN,
            "No implicit yield published (e.g. all bids rejected): "
            + ", ".join(sorted({d.date().isoformat() for d in no_yield["date"]})),
        )
    revised = df[df["exclusion_reason"] == "superseded_revision"]
    if len(revised):
        q.add(
            "edition_revisions",
            CheckStatus.WARN,
            f"{len(revised)} auction(s) differ between Handbook editions; latest edition kept",
        )
    else:
        overlap = int((df["exclusion_reason"] == "duplicate_identical").sum())
        q.add(
            "edition_revisions",
            CheckStatus.PASS,
            f"{overlap} overlapping auction(s) identical across editions",
        )
    return scope
