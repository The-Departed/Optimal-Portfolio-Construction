import numpy as np
import pandas as pd

from app.data_pipeline.normalization import (
    normalize_dates,
    parse_rbi_auction_table,
    parse_rbi_holiday_page,
    to_numeric_flagged,
)
from tests.fixtures.synthetic import rbi_auction_html, rbi_holiday_html


def test_timezone_aware_dates_use_exchange_local_date() -> None:
    raw = pd.Series(["2024-01-02 00:00:00+05:30", "2024-01-02T20:00:00Z", "2024-01-03"])
    out = normalize_dates(raw)
    # 20:00 UTC on Jan 2 is 01:30 IST on Jan 3: the session date must not shift back.
    assert list(out.dt.date.astype(str)) == ["2024-01-02", "2024-01-03", "2024-01-03"]
    assert out.dt.tz is None


def test_explicit_format_and_malformed_dates() -> None:
    out = normalize_dates(pd.Series(["02-Jan-2024", "31-Feb-2024", "garbage"]), fmt="%d-%b-%Y")
    assert out.iloc[0] == pd.Timestamp("2024-01-02")
    assert out.iloc[1:].isna().all()


def test_numeric_conversion_flags_without_coercion() -> None:
    raw = pd.Series(["101.5", "", "-", "N.A.", "12,5", "abc", "inf", " 7 "])
    values, missing, non_numeric = to_numeric_flagged(raw)
    assert values.iloc[0] == 101.5 and values.iloc[-1] == 7.0
    assert list(missing) == [False, True, True, True, False, False, False, False]
    assert list(non_numeric) == [False, False, False, False, True, True, False, False]
    assert np.isinf(values.iloc[6])


def test_rbi_table_columns_located_by_header_not_footnote() -> None:
    # The footnote spans every column and mentions "implicit yield": regression test.
    html = rbi_auction_html(
        [
            ("02-Jan-2024", "04-Jan-2024", "98.40", "6.5000"),
            ("09-Jan-2024", "11-Jan-2024", "-", "-"),
        ],
        "Auctions of 91-Day Government of India Treasury Bills",
    )
    df = parse_rbi_auction_table(html)
    assert list(df["raw_value"]) == ["6.5000", "-"]
    assert list(df["raw_cut_off_price"]) == ["98.40", "-"]
    assert df["issue_date"].iloc[0] == pd.Timestamp("2024-01-04")


def test_rbi_holiday_page_parses_month_sections() -> None:
    html = rbi_holiday_html(
        2024, {"2024-01-26": "Republic Day", "2024-03-08": "Mahashivratri", "2024-03-25": "Holi"}
    )
    df = parse_rbi_holiday_page(html, 2024)
    assert list(df["date"].dt.date.astype(str)) == ["2024-01-26", "2024-03-08", "2024-03-25"]
    assert df["raw_value"].iloc[2] == "Holi"
