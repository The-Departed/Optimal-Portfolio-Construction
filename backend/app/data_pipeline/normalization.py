"""Parse raw snapshots into normalized, typed record tables.

Normalization never drops records: malformed dates and values are kept with
``value``/``date`` set to missing so that cleaning can flag and report them.

Normalized columns (all sources): ``date`` (timezone-naive trading/auction date),
``raw_value`` (source text of the selected field), ``value`` (float or NaN) and
``source_file``. Sources add their own descriptive columns.
"""

import io
from datetime import date

import numpy as np
import pandas as pd

from app.data_pipeline.raw_store import RawSnapshot
from app.data_pipeline.source_registry import DatasetSpec, SourceKind, ValueKind

MARKET_TZ = "Asia/Kolkata"
MISSING_MARKERS = frozenset({"", "-", "--", "na", "n.a.", "n/a", "nan", "null", "none"})


def normalize_dates(raw: pd.Series, *, fmt: str | None = None) -> pd.Series:
    """Convert date strings to timezone-naive midnight dates in exchange local time.

    Timezone-aware timestamps are converted to Asia/Kolkata before the time is
    dropped, so a session's date never shifts across midnight. Unparseable values
    become NaT.
    """
    text = raw.astype("string").str.strip()
    if fmt is not None:
        parsed = pd.to_datetime(text, format=fmt, errors="coerce")
        return parsed.dt.normalize()
    has_offset = text.str.contains(r"(?:[+-]\d{2}:?\d{2}|Z)$", regex=True, na=False)
    out = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    if has_offset.any():
        aware = pd.to_datetime(text[has_offset], utc=True, errors="coerce", format="ISO8601")
        out.loc[has_offset] = aware.dt.tz_convert(MARKET_TZ).dt.tz_localize(None)
    if (~has_offset).any():
        out.loc[~has_offset] = pd.to_datetime(text[~has_offset], errors="coerce", format="ISO8601")
    return out.dt.normalize()


def to_numeric_flagged(raw: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return ``(values, is_missing, is_non_numeric)`` without coercing bad input.

    ``is_missing``: empty or an explicit missing marker ("-", "N.A.", ...).
    ``is_non_numeric``: present but not parseable as a number. Both yield NaN values.
    Infinite values are parsed as such and flagged later.
    """
    text = raw.astype("string").str.strip()
    is_missing = text.isna() | text.str.lower().isin(MISSING_MARKERS)
    values = pd.to_numeric(text.where(~is_missing), errors="coerce").astype("float64")
    is_non_numeric = ~is_missing & values.isna()
    return values, is_missing.astype(bool), is_non_numeric.astype(bool)


def _yahoo(spec: DatasetSpec, snapshot: RawSnapshot) -> pd.DataFrame:
    raw = pd.read_csv(io.BytesIO(snapshot.file("history.csv").content), dtype=str)
    field = spec.source.value_field
    if field not in raw.columns:
        raise ValueError(f"{spec.dataset_id}: column {field!r} missing from Yahoo data")
    out = pd.DataFrame(
        {
            "date": normalize_dates(raw["Date"]),
            "source_timestamp": raw["Date"],
            "raw_value": raw[field],
            "close": pd.to_numeric(raw.get("Close"), errors="coerce"),
            "adj_close": pd.to_numeric(raw.get("Adj Close"), errors="coerce"),
            "volume": pd.to_numeric(raw.get("Volume"), errors="coerce"),
            "dividends": pd.to_numeric(raw.get("Dividends"), errors="coerce"),
            "stock_splits": pd.to_numeric(raw.get("Stock Splits"), errors="coerce"),
            "source_file": "history.csv",
        }
    )
    return out


def _amfi(spec: DatasetSpec, snapshot: RawSnapshot) -> pd.DataFrame:
    frames = []
    for f in sorted(snapshot.files, key=lambda x: x.name):
        lines = f.content.decode("utf-8").splitlines()
        header = lines[0].split(";")
        rows = [line.split(";") for line in lines[1:] if line.strip()]
        df = pd.DataFrame(rows, columns=header, dtype=str)
        df["source_file"] = f.name
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    return pd.DataFrame(
        {
            "date": normalize_dates(raw["Date"], fmt="%d-%b-%Y"),
            "source_timestamp": raw["Date"],
            "raw_value": raw[spec.source.value_field],
            "scheme_code": raw["Scheme Code"],
            "scheme_name": raw["NAV Name"],
            "isin": raw["ISIN Div Payout/ISIN Growth"],
            "source_file": raw["source_file"],
        }
    )


def _find_column(headers: pd.DataFrame, needle: str) -> int:
    for col in headers.columns:
        if headers[col].astype(str).str.contains(needle, case=False, regex=False).any():
            return int(col)
    raise ValueError(f"RBI table has no column matching {needle!r}")


def parse_rbi_auction_table(page_html: str) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(page_html))
    # The page layout itself is a table that mentions the column titles, so pick the
    # largest table containing the header rather than the first.
    candidates = [
        t
        for t in tables
        if t.astype(str).apply(lambda c: c.str.contains("Date of Auction")).any().any()
    ]
    if not candidates:
        raise ValueError("RBI page has no auction table")
    table = max(candidates, key=lambda t: t.shape[0] * t.shape[1])
    table = table.copy()
    table.columns = range(table.shape[1])
    first_col = table[0].astype(str)
    auction = pd.to_datetime(first_col.str.strip(), format="%d-%b-%Y", errors="coerce")
    if auction.notna().sum() == 0:
        raise ValueError("RBI auction table has no dated rows")
    # Only rows above the first auction are headers; footnotes below the data repeat
    # column titles across merged cells and must not be used to locate columns.
    first_data = int(auction.notna().to_numpy().argmax())
    header_rows = table.iloc[:first_data]
    yield_col = _find_column(header_rows, "Implicit Yield")
    price_col = _find_column(header_rows, "Cut-off Price")
    issue_col = _find_column(header_rows, "Date of Issue")
    data = table[auction.notna()]
    return pd.DataFrame(
        {
            "date": auction[auction.notna()].dt.normalize(),
            "source_timestamp": data[0].astype(str).str.strip(),
            "issue_date": pd.to_datetime(
                data[issue_col].astype(str).str.strip(), format="%d-%b-%Y", errors="coerce"
            ),
            "raw_value": data[yield_col].astype(str),
            "raw_cut_off_price": data[price_col].astype(str),
        }
    ).reset_index(drop=True)


def _rbi(spec: DatasetSpec, snapshot: RawSnapshot) -> pd.DataFrame:
    editions = {e["page_id"]: e for e in snapshot.source_metadata.get("editions", [])}
    frames = []
    for f in snapshot.files:
        df = parse_rbi_auction_table(f.content.decode("utf-8"))
        page_id = f.name.rsplit("_pv", 1)[-1].removesuffix(".html")
        df["edition_year"] = int(
            editions.get(page_id, {}).get("edition_year", f.name.split("_")[2])
        )
        df["page_id"] = page_id
        df["source_file"] = f.name
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    price, _, _ = to_numeric_flagged(out["raw_cut_off_price"])
    out["cut_off_price"] = price
    return out


_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}


def parse_rbi_holiday_page(page_html: str, year: int) -> pd.DataFrame:
    """Rows of the RBI holiday matrix: a month row followed by (day, name, type) rows."""
    tables = pd.read_html(io.StringIO(page_html))
    table = max(tables, key=lambda t: t.shape[0] * t.shape[1])
    first_month = str(table.columns[0]).split(".")[0]
    if first_month not in _MONTHS:
        raise ValueError("RBI holiday page has no month-structured table")
    month = _MONTHS[first_month]
    rows = []
    for cells in table.astype(str).itertuples(index=False):
        head = cells[0].strip()
        if head in _MONTHS:
            month = _MONTHS[head]
            continue
        day = pd.to_numeric(head, errors="coerce")
        holiday = pd.Timestamp(year=year, month=month, day=int(day)) if pd.notna(day) else pd.NaT
        rows.append(
            {
                "date": holiday,
                "source_timestamp": f"{year}-{month:02d}-{head}",
                "raw_value": cells[1].strip(),
                "holiday_type": cells[2].strip(),
            }
        )
    return pd.DataFrame(rows)


def _rbi_holidays(spec: DatasetSpec, snapshot: RawSnapshot) -> pd.DataFrame:
    frames = []
    for f in snapshot.files:
        year = int(f.name.removesuffix(".html").rsplit("_", 1)[-1])
        df = parse_rbi_holiday_page(f.content.decode("utf-8"), year)
        df["source_file"] = f.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


_PARSERS = {
    SourceKind.YAHOO: _yahoo,
    SourceKind.AMFI_NAV: _amfi,
    SourceKind.RBI_HANDBOOK: _rbi,
    SourceKind.RBI_HOLIDAYS: _rbi_holidays,
}


def normalize(spec: DatasetSpec, snapshot: RawSnapshot) -> pd.DataFrame:
    """Parse a snapshot into a record table sorted by date (NaT last)."""
    df = _PARSERS[spec.source.kind](spec, snapshot)
    if spec.value_kind is ValueKind.CALENDAR:
        # Date lists carry no numeric value; only the date is validated.
        df["value"] = np.nan
        for flag in ("is_missing", "is_non_numeric", "is_non_finite"):
            df[flag] = False
        df["is_invalid_date"] = df["date"].isna()
        df["dataset_id"] = spec.dataset_id
        return df.sort_values("date", kind="stable", na_position="last").reset_index(drop=True)
    values, is_missing, is_non_numeric = to_numeric_flagged(df["raw_value"])
    df["value"] = values
    df["is_missing"] = is_missing
    df["is_non_numeric"] = is_non_numeric
    df["is_non_finite"] = np.isinf(values.to_numpy())
    df["is_invalid_date"] = df["date"].isna()
    df["dataset_id"] = spec.dataset_id
    return df.sort_values("date", kind="stable", na_position="last").reset_index(drop=True)


def requested_window(start: date, end: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(start), pd.Timestamp(end)
