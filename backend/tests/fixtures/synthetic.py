"""SYNTHETIC test fixtures for the data pipeline.

Everything here is generated for automated tests only. These values are NOT market
data and must never be written to the project's data/ directory or presented as
real observations. Fake downloaders emit raw files in each real source's format so
the full normalize -> clean -> validate -> align path is exercised offline.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from app.data_pipeline.downloaders.base import DownloadContext, DownloadError
from app.data_pipeline.raw_store import RawFile, RawSnapshot
from app.data_pipeline.source_registry import DatasetSpec, SourceKind

STUDY_START = date(2024, 1, 1)
STUDY_END = date(2024, 3, 29)
EXCHANGE_HOLIDAY = pd.Timestamp("2024-01-26")  # synthetic exchange + bank holiday
BANK_ONLY_HOLIDAY = pd.Timestamp("2024-02-19")  # bank holiday on which equities trade
SYNTHETIC_HOLIDAYS = {
    "2024-01-26": "Republic Day",
    "2024-02-19": "Synthetic bank holiday",
    "2024-03-08": "Synthetic holiday 3",
    "2024-03-25": "Synthetic holiday 4",
    "2024-04-09": "Synthetic holiday 5",
    "2024-05-01": "Synthetic holiday 6",
    "2024-06-17": "Synthetic holiday 7",
    "2024-08-15": "Synthetic holiday 8",
    "2024-10-02": "Synthetic holiday 9",
    "2024-11-01": "Synthetic holiday 10",
    "2024-12-25": "Synthetic holiday 11",
}


def trading_days(start: date = STUDY_START, end: date = STUDY_END) -> pd.DatetimeIndex:
    days = pd.bdate_range(start, end)
    return days[days != EXCHANGE_HOLIDAY]


@dataclass
class Scenario:
    """Knobs that inject specific data problems into the synthetic sources."""

    fail: set[str] = field(default_factory=set)
    drop_dates: dict[str, list[str]] = field(default_factory=dict)
    duplicate_dates: dict[str, list[str]] = field(default_factory=dict)
    late_start: dict[str, str] = field(default_factory=dict)
    bad_values: dict[str, dict[str, str]] = field(default_factory=dict)
    scale_dates: dict[str, dict[str, float]] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)


def _path(seed: int, n: int, start: float, vol: float = 0.01) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return start * np.cumprod(1 + rng.normal(0.0003, vol, n))


def _seed(dataset_id: str) -> int:
    return sum(ord(c) for c in dataset_id)


def _dates_for(spec: DatasetSpec, scenario: Scenario) -> pd.DatetimeIndex:
    days = trading_days()
    if spec.dataset_id in ("GSEC", "GOLD_NAV"):
        days = days[days != BANK_ONLY_HOLIDAY]  # no NAV on a bank holiday
    if spec.dataset_id in scenario.late_start:
        days = days[days >= pd.Timestamp(scenario.late_start[spec.dataset_id])]
    drops = pd.DatetimeIndex(scenario.drop_dates.get(spec.dataset_id, []))
    return days.difference(drops)


def _values(spec: DatasetSpec, dates: pd.DatetimeIndex, scenario: Scenario) -> list[str]:
    base = 30.0 if spec.dataset_id in ("GOLD", "GOLD_NAV") else 100.0
    full = trading_days()
    # GOLD and GOLD_NAV share one path so the cross-check is meaningful.
    key = "GOLD" if spec.dataset_id.startswith("GOLD") else spec.dataset_id
    path = pd.Series(_path(_seed(key), len(full), base), index=full)
    vals = path.loc[dates].copy()
    for d, factor in scenario.scale_dates.get(spec.dataset_id, {}).items():
        vals.loc[pd.Timestamp(d)] *= factor
    out = [f"{v:.4f}" for v in vals]
    for d, text in scenario.bad_values.get(spec.dataset_id, {}).items():
        out[list(dates).index(pd.Timestamp(d))] = text
    return out


def _with_duplicates(
    rows: list[list[str]], dates: pd.DatetimeIndex, dups: list[str]
) -> list[list[str]]:
    out = list(rows)
    for d in dups:
        out.append(rows[list(dates).index(pd.Timestamp(d))])
    return out


def _snapshot(spec: DatasetSpec, files: list[RawFile], meta: dict | None = None) -> RawSnapshot:
    return RawSnapshot(
        dataset_id=spec.dataset_id,
        source_kind=spec.source.kind.value,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        files=files,
        request={"synthetic": True},
        source_metadata=meta or {},
    )


def _yahoo(spec: DatasetSpec, scenario: Scenario) -> RawSnapshot:
    dates = _dates_for(spec, scenario)
    vals = _values(spec, dates, scenario)
    rows = [
        [f"{d.date()} 00:00:00+05:30", v, v, v, v, v, "1000", "0.0", "0.0"]
        for d, v in zip(dates, vals, strict=True)
    ]
    rows = _with_duplicates(rows, dates, scenario.duplicate_dates.get(spec.dataset_id, []))
    header = "Date,Open,High,Low,Close,Adj Close,Volume,Dividends,Stock Splits"
    csv = "\n".join([header, *(",".join(r) for r in rows)]) + "\n"
    meta = {
        "symbol": spec.source.identifier,
        "longName": spec.source.expected_name,
        "currency": "INR",
    }
    return _snapshot(
        spec,
        [
            RawFile("history.csv", csv.encode()),
            RawFile("history_metadata.json", json.dumps(meta).encode()),
        ],
        meta,
    )


def _amfi(spec: DatasetSpec, scenario: Scenario) -> RawSnapshot:
    dates = _dates_for(spec, scenario)
    vals = _values(spec, dates, scenario)
    isin = spec.source.params["isin"]
    rows = [
        [
            spec.source.identifier,
            spec.source.expected_name,
            "Direct Plan",
            "",
            isin,
            "",
            v,
            d.strftime("%d-%b-%Y"),
        ]
        for d, v in zip(dates, vals, strict=True)
    ]
    rows = _with_duplicates(rows, dates, scenario.duplicate_dates.get(spec.dataset_id, []))
    header = (
        "Scheme Code;NAV Name;Plan;Option;ISIN Div Payout/ISIN Growth;"
        "ISIN Div Reinvestment;Net Asset Value;Date"
    )
    text = "\n".join([header, *(";".join(r) for r in rows)]) + "\n"
    return _snapshot(spec, [RawFile("nav_2024.txt", text.encode())])


def rbi_auction_html(rows: list[tuple[str, str, str, str]], title: str) -> str:
    """Minimal replica of the RBI Handbook table, including a full-width footnote."""
    head = (
        "<tr><td>Date of Auction</td><td>Date of Issue</td><td>Notified Amount</td>"
        "<td>Cut-off Price (₹)</td><td>Implicit Yield at Cut-off Price (percent)</td></tr>"
    )
    body = "".join(
        f"<tr><td>{a}</td><td>{i}</td><td>9000</td><td>{p}</td><td>{y}</td></tr>"
        for a, i, p, y in rows
    )
    foot = (
        '<tr><td colspan="5">Note : The presentation of implicit yield at cut-off price is '
        "based on actual/ 365 day count convention.</td></tr>"
    )
    return (
        f"<html><body><h2>{title}</h2><table><tr><td>layout Date of Auction</td></tr></table>"
        f"<table>{head}<tr><td>2023-24</td><td></td><td></td><td></td><td></td></tr>{body}{foot}"
        "</table></body></html>"
    )


def _rbi(spec: DatasetSpec, scenario: Scenario) -> RawSnapshot:
    start = pd.Timestamp(STUDY_START) - pd.Timedelta(days=14)
    auctions = pd.date_range(start, pd.Timestamp(STUDY_END), freq="7D")
    rows = []
    for k, a in enumerate(auctions):
        y = 6.5 + 0.01 * k
        price = 100 / (1 + y / 100 * 91 / 365)
        rows.append(
            (
                a.strftime("%d-%b-%Y"),
                (a + timedelta(days=1)).strftime("%d-%b-%Y"),
                f"{price:.2f}",
                f"{y:.4f}",
            )
        )
    for d, text in scenario.bad_values.get(spec.dataset_id, {}).items():
        idx = [r[0] for r in rows].index(pd.Timestamp(d).strftime("%d-%b-%Y"))
        rows[idx] = (rows[idx][0], rows[idx][1], "-", text)
    html = rbi_auction_html(rows, spec.source.expected_name)
    meta = {"editions": [{"edition_year": "2024", "page_id": "1"}], "missing_editions": []}
    return _snapshot(spec, [RawFile("rbi_hbs_2024_pv1.html", html.encode())], meta)


def rbi_holiday_html(year: int, holidays: dict[str, str]) -> str:
    by_month: dict[str, list[tuple[int, str]]] = {}
    for d, name in sorted(holidays.items()):
        ts = pd.Timestamp(d)
        if ts.year == year:
            by_month.setdefault(ts.month_name(), []).append((ts.day, name))
    months = list(by_month)
    first = months[0]
    rows = [f"<tr><th>{first}</th><th>{first}</th><th>{first}</th></tr>"]
    for i, m in enumerate(months):
        if i:
            rows.append(f"<tr><td>{m}</td><td>{m}</td><td>{m}</td></tr>")
        rows += [
            f"<tr><td>{day}</td><td>{name}</td><td>•Holiday under NI Act</td></tr>"
            for day, name in by_month[m]
        ]
    return (
        f"<html><body><p>Mumbai regional office holiday list for the year {year}</p>"
        f"<table>{''.join(rows)}</table></body></html>"
    )


def _holidays(spec: DatasetSpec, scenario: Scenario) -> RawSnapshot:
    html = rbi_holiday_html(2024, SYNTHETIC_HOLIDAYS)
    return _snapshot(spec, [RawFile("rbi_holidays_28_2024.html", html.encode())])


_BUILDERS: dict[SourceKind, Callable[[DatasetSpec, Scenario], RawSnapshot]] = {
    SourceKind.YAHOO: _yahoo,
    SourceKind.AMFI_NAV: _amfi,
    SourceKind.RBI_HANDBOOK: _rbi,
    SourceKind.RBI_HOLIDAYS: _holidays,
}


def fake_downloaders(scenario: Scenario | None = None) -> dict[SourceKind, Callable]:
    scenario = scenario or Scenario()

    def make(kind: SourceKind) -> Callable[[DatasetSpec, DownloadContext], RawSnapshot]:
        def download(spec: DatasetSpec, ctx: DownloadContext) -> RawSnapshot:
            scenario.calls.append(spec.dataset_id)
            if spec.dataset_id in scenario.fail:
                raise DownloadError(f"synthetic network failure for {spec.dataset_id}")
            return _BUILDERS[kind](spec, scenario)

        return download

    return {kind: make(kind) for kind in _BUILDERS}
