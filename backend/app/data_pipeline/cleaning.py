"""Record-level cleaning rules.

Every rule flags records first and records an ``exclusion_reason``; nothing is
repaired, interpolated or forward-filled. Rules, in order of precedence:

1. ``invalid_date``       unparseable date
2. ``missing_value``      empty / explicit missing marker in the selected field
3. ``non_numeric``        present but not a number
4. ``non_finite``         +/-inf
5. ``non_positive``       price, NAV or index level <= 0
6. ``out_of_range``       yield outside the plausible range
7. ``duplicate_*``        repeated dates (see ``resolve_duplicates``)
8. ``source_error``       deviates from an independent reference beyond threshold
"""

import numpy as np
import pandas as pd

from app.data_pipeline.config import QualityThresholds
from app.data_pipeline.source_registry import CorporateAction, DatasetSpec, ValueKind


def _exclude(df: pd.DataFrame, mask: pd.Series, reason: str) -> None:
    target = mask & ~df["excluded"]
    df.loc[target, "exclusion_reason"] = reason
    df.loc[target, "excluded"] = True


def apply_value_rules(df: pd.DataFrame, spec: DatasetSpec, t: QualityThresholds) -> pd.DataFrame:
    df = df.copy()
    df["excluded"] = False
    df["exclusion_reason"] = pd.Series(pd.NA, index=df.index, dtype="string")
    _exclude(df, df["is_invalid_date"], "invalid_date")
    if spec.value_kind is ValueKind.CALENDAR:
        return df
    _exclude(df, df["is_missing"], "missing_value")
    _exclude(df, df["is_non_numeric"], "non_numeric")
    _exclude(df, df["is_non_finite"], "non_finite")
    if spec.value_kind is ValueKind.YIELD:
        out = (df["value"] < t.rf_min_yield_pct) | (df["value"] > t.rf_max_yield_pct)
        _exclude(df, out.fillna(False), "out_of_range")
    else:
        _exclude(df, (df["value"] <= 0).fillna(False), "non_positive")
    return df


def resolve_duplicates(df: pd.DataFrame, *, prefer_column: str | None = None) -> pd.DataFrame:
    """Resolve repeated dates among records that are otherwise valid.

    Default (prices): identical repeats keep the first record
    (``duplicate_identical``); conflicting repeats are all excluded
    (``duplicate_conflict``) because there is no defensible way to choose.

    With ``prefer_column`` (risk-free editions): the record with the highest value
    of that column (latest publication) is kept; others are excluded as
    ``duplicate_identical`` or ``superseded_revision``.
    """
    df = df.copy()
    df["is_duplicate_date"] = df.duplicated("date", keep=False) & df["date"].notna()
    valid = df[~df["excluded"]]
    if valid["value"].isna().all():
        # Date lists (no values): repeated dates are identical by definition.
        repeat = valid.duplicated("date", keep="first")
        df.loc[repeat[repeat].index, ["excluded", "exclusion_reason"]] = [
            True,
            "duplicate_identical",
        ]
        return df
    for _, group in valid[valid.duplicated("date", keep=False)].groupby("date"):
        values = group["value"]
        identical = np.allclose(values, values.iloc[0], rtol=0, atol=1e-12)
        if prefer_column is not None:
            keep = group[prefer_column].idxmax()
            drop = group.index.drop(keep)
            reason = "duplicate_identical" if identical else "superseded_revision"
            df.loc[drop, ["excluded", "exclusion_reason"]] = [True, reason]
        elif identical:
            df.loc[group.index[1:], ["excluded", "exclusion_reason"]] = [
                True,
                "duplicate_identical",
            ]
        else:
            df.loc[group.index, ["excluded", "exclusion_reason"]] = [True, "duplicate_conflict"]
    return df


def split_adjusted(values: pd.Series, actions: tuple[CorporateAction, ...]) -> pd.Series:
    """Express a date-indexed unadjusted series in post-split units.

    Used only to compare an unadjusted series (e.g. AMFI NAV) with a split-adjusted
    one. It is never applied to a series that the source has already adjusted.
    """
    adjusted = values.astype("float64").copy()
    for action in actions:
        if action.kind == "unit_split":
            adjusted.loc[adjusted.index < pd.Timestamp(action.effective_date)] /= action.ratio
    return adjusted


def flag_reference_deviation(
    df: pd.DataFrame, reference: pd.Series, threshold: float, *, exclude: bool
) -> pd.DataFrame:
    """Compare each valid record with a date-matched reference value.

    Adds ``reference_value`` and ``reference_deviation`` (value / reference - 1).
    When ``exclude`` is true, records beyond ``threshold`` become ``source_error``.
    """
    df = df.copy()
    ref = df["date"].map(reference)
    df["reference_value"] = ref
    df["reference_deviation"] = df["value"] / ref - 1.0
    beyond = (df["reference_deviation"].abs() > threshold).fillna(False) & ~df["excluded"]
    df["is_source_error"] = beyond if exclude else False
    if exclude:
        _exclude(df, beyond, "source_error")
    return df


def valid_series(df: pd.DataFrame) -> pd.Series:
    """Date-indexed values of records that survived cleaning."""
    kept = df[~df["excluded"]]
    return pd.Series(kept["value"].to_numpy(), index=pd.DatetimeIndex(kept["date"]), name="value")
