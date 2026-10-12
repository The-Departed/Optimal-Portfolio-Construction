from datetime import date

import numpy as np
import pandas as pd

from app.data_pipeline import cleaning
from app.data_pipeline.config import DEFAULT_THRESHOLDS
from app.data_pipeline.source_registry import BY_ID, CorporateAction


def _records(dates: list[str], raw: list[str]) -> pd.DataFrame:
    values = pd.to_numeric(pd.Series(raw), errors="coerce")
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates, errors="coerce"),
            "raw_value": raw,
            "value": values,
            "is_missing": [r in ("", "-") for r in raw],
            "is_non_numeric": [
                r not in ("", "-") and np.isnan(v) for r, v in zip(raw, values, strict=True)
            ],
            "is_non_finite": np.isinf(values),
            "is_invalid_date": pd.to_datetime(dates, errors="coerce").isna(),
        }
    )


def test_invalid_prices_are_flagged_then_excluded() -> None:
    df = _records(
        ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "bad", "2024-01-05"],
        ["10", "0", "-3", "", "11", "abc"],
    )
    out = cleaning.apply_value_rules(df, BY_ID["TCS"], DEFAULT_THRESHOLDS)
    assert list(out["exclusion_reason"].fillna("")) == [
        "",
        "non_positive",
        "non_positive",
        "missing_value",
        "invalid_date",
        "non_numeric",
    ]
    assert cleaning.valid_series(out).tolist() == [10.0]


def test_yields_use_range_check_not_positivity() -> None:
    df = _records(["2024-01-01", "2024-01-08", "2024-01-15"], ["6.5", "98.4", "-0.1"])
    out = cleaning.apply_value_rules(df, BY_ID["RF_TBILL_91D"], DEFAULT_THRESHOLDS)
    assert list(out["exclusion_reason"].fillna("")) == ["", "out_of_range", "out_of_range"]


def test_duplicate_dates_identical_kept_once_conflicts_excluded() -> None:
    df = _records(
        ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"],
        ["10", "10", "11", "12", "13"],
    )
    out = cleaning.resolve_duplicates(
        cleaning.apply_value_rules(df, BY_ID["TCS"], DEFAULT_THRESHOLDS)
    )
    assert list(out["exclusion_reason"].fillna("")) == [
        "",
        "duplicate_identical",
        "duplicate_conflict",
        "duplicate_conflict",
        "",
    ]
    assert out["is_duplicate_date"].sum() == 4


def test_duplicate_editions_keep_latest_publication() -> None:
    df = _records(
        ["2024-01-01", "2024-01-01", "2024-01-08", "2024-01-08"], ["6.5", "6.5", "6.6", "6.7"]
    )
    df["edition_year"] = [2023, 2024, 2023, 2024]
    out = cleaning.resolve_duplicates(
        cleaning.apply_value_rules(df, BY_ID["RF_TBILL_91D"], DEFAULT_THRESHOLDS),
        prefer_column="edition_year",
    )
    assert list(out["exclusion_reason"].fillna("")) == [
        "duplicate_identical",
        "",
        "superseded_revision",
        "",
    ]


def test_split_adjustment_only_before_effective_date() -> None:
    s = pd.Series(
        [3300.0, 3360.0, 33.7], index=pd.to_datetime(["2019-12-19", "2019-12-20", "2019-12-23"])
    )
    action = CorporateAction("unit_split", date(2019, 12, 23), 100.0, "")
    assert cleaning.split_adjusted(s, (action,)).tolist() == [33.0, 33.6, 33.7]


def test_reference_deviation_marks_source_errors() -> None:
    df = _records(["2024-01-01", "2024-01-02", "2024-01-03"], ["33.5", "0.335", "33.6"])
    df = cleaning.apply_value_rules(df, BY_ID["GOLD"], DEFAULT_THRESHOLDS)
    ref = pd.Series(
        [33.4, 33.5, 33.6], index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    )
    out = cleaning.flag_reference_deviation(df, ref, 0.2, exclude=True)
    assert list(out["exclusion_reason"].fillna("")) == ["", "source_error", ""]
    report_only = cleaning.flag_reference_deviation(df, ref, 0.2, exclude=False)
    assert not report_only["excluded"].any()
