from datetime import date

import pandas as pd
import pytest

from app.data_pipeline.config import DEFAULT_THRESHOLDS
from app.data_pipeline.quality_checks import (
    CheckStatus,
    DatasetQuality,
    DatasetStatus,
    OverallStatus,
    check_daily_coverage,
    check_risk_free,
    implied_yield_pct,
    overall_status,
)

CAL = pd.bdate_range("2024-01-01", "2024-03-29")


def _checks(q: DatasetQuality) -> dict[str, CheckStatus]:
    return {c.name: c.status for c in q.checks}


def test_dataset_status_from_checks() -> None:
    q = DatasetQuality("X")
    q.add("a", CheckStatus.PASS, "")
    assert q.status is DatasetStatus.PASS
    q.add("b", CheckStatus.WARN, "")
    assert q.status is DatasetStatus.PASS_WITH_WARNINGS
    q.add("c", CheckStatus.FAIL, "")
    assert q.status is DatasetStatus.FAIL
    assert DatasetQuality("Y", retrieved=False).status is DatasetStatus.NOT_RETRIEVED


@pytest.mark.parametrize(
    ("statuses", "warnings", "expected"),
    [
        ({"A": DatasetStatus.PASS}, False, OverallStatus.PASS),
        ({"A": DatasetStatus.PASS}, True, OverallStatus.PASS_WITH_WARNINGS),
        (
            {"A": DatasetStatus.PASS, "X": DatasetStatus.FAIL},
            False,
            OverallStatus.PASS_WITH_WARNINGS,
        ),
        ({"A": DatasetStatus.FAIL}, False, OverallStatus.BLOCKED),
        ({"A": DatasetStatus.NOT_RETRIEVED}, False, OverallStatus.BLOCKED),
        ({}, False, OverallStatus.BLOCKED),  # a critical dataset that never ran
    ],
)
def test_overall_status(statuses, warnings, expected) -> None:
    assert overall_status(statuses, {"A"}, alignment_ok=True, has_warnings=warnings) is expected


def test_overall_blocked_when_alignment_fails() -> None:
    s = {"A": DatasetStatus.PASS}
    assert overall_status(s, {"A"}, alignment_ok=False, has_warnings=False) is OverallStatus.BLOCKED


def test_full_coverage_passes() -> None:
    q = DatasetQuality("X")
    check_daily_coverage(
        q, pd.Series(1.0, index=CAL), CAL, date(2024, 1, 1), date(2024, 3, 29), DEFAULT_THRESHOLDS
    )
    assert set(_checks(q).values()) == {CheckStatus.PASS}
    assert q.coverage["session_coverage"] == 1.0


def test_insufficient_coverage_and_long_gaps_fail() -> None:
    q = DatasetQuality("X")
    series = pd.Series(1.0, index=CAL[CAL >= "2024-02-15"])  # starts six weeks late
    check_daily_coverage(q, series, CAL, date(2024, 1, 1), date(2024, 3, 29), DEFAULT_THRESHOLDS)
    checks = _checks(q)
    assert checks["period_boundaries"] is CheckStatus.FAIL
    assert checks["session_coverage"] is CheckStatus.FAIL
    assert checks["longest_gap"] is CheckStatus.FAIL
    assert q.status is DatasetStatus.FAIL


def test_explained_non_valuation_days_do_not_count_as_missing() -> None:
    holiday = pd.Timestamp("2024-02-19")
    series = pd.Series(1.0, index=CAL.drop(holiday))
    q = DatasetQuality("X")
    check_daily_coverage(
        q,
        series,
        CAL,
        date(2024, 1, 1),
        date(2024, 3, 29),
        DEFAULT_THRESHOLDS,
        {holiday: "RBI Mumbai bank holiday: x"},
    )
    assert q.coverage["sessions_missing"] == 0
    assert q.coverage["sessions_not_expected"] == 1
    assert _checks(q)["expected_non_valuation_days"] is CheckStatus.WARN
    q2 = DatasetQuality("Y")
    check_daily_coverage(q2, series, CAL, date(2024, 1, 1), date(2024, 3, 29), DEFAULT_THRESHOLDS)
    assert q2.coverage["missing_session_dates"] == ["2024-02-19"]


def _rf_records(yields: list[float], start: str = "2023-12-20", step: int = 7) -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(yields), freq=f"{step}D")
    prices = [100 / (1 + y / 100 * 91 / 365) for y in yields]
    return pd.DataFrame(
        {
            "date": dates,
            "value": yields,
            "cut_off_price": [round(p, 2) for p in prices],
            "excluded": False,
            "exclusion_reason": pd.Series([pd.NA] * len(yields), dtype="string"),
        }
    )


def test_implied_yield_formula() -> None:
    assert implied_yield_pct(pd.Series([98.40]), 91, 365).iloc[0] == pytest.approx(
        (100 / 98.4 - 1) * 365 / 91 * 100
    )


def test_risk_free_weekly_percent_series_passes() -> None:
    q = DatasetQuality("RF")
    check_risk_free(
        q,
        _rf_records([6.5 + 0.01 * k for k in range(16)]),
        date(2024, 1, 1),
        date(2024, 3, 29),
        DEFAULT_THRESHOLDS,
    )
    checks = _checks(q)
    assert checks["units"] is CheckStatus.PASS
    assert checks["frequency"] is CheckStatus.PASS
    assert checks["price_yield_consistency"] is CheckStatus.PASS
    assert checks["period_boundaries"] is CheckStatus.PASS


def test_risk_free_rejects_values_that_look_like_prices_or_decimals() -> None:
    for values in ([98.4] * 16, [0.065] * 16):
        df = _rf_records([6.5] * 16)
        df["value"] = values
        q = DatasetQuality("RF")
        check_risk_free(q, df, date(2024, 1, 1), date(2024, 3, 29), DEFAULT_THRESHOLDS)
        assert _checks(q)["units"] is CheckStatus.FAIL


def test_risk_free_frequency_metadata() -> None:
    q = DatasetQuality("RF")
    check_risk_free(
        q, _rf_records([6.5] * 4, step=30), date(2024, 1, 1), date(2024, 3, 29), DEFAULT_THRESHOLDS
    )
    assert _checks(q)["frequency"] is CheckStatus.FAIL  # monthly is not the expected weekly
    assert q.coverage["median_gap_days"] == 30
