"""Schema and value checks for processed CSV files.

These checks guard the analytics layer against missing, malformed or inconsistent
files. They never repair data: any violation raises ``DatasetLoadError``.
"""

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd


class DatasetLoadError(ValueError):
    """A required processed artifact is missing or violates its schema."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message)
        self.path = str(path) if path is not None else None


def read_dated_csv(
    path: Path,
    *,
    date_column: str,
    value_columns: Sequence[str],
    exact_columns: bool = True,
) -> pd.DataFrame:
    """Read a CSV keyed by ISO dates into a float frame with a DatetimeIndex."""
    if not path.is_file():
        raise DatasetLoadError(
            f"Required file {path.name} is missing. Re-run the data pipeline "
            "(uv run python -m scripts.download_datasets).",
            path=path,
        )
    try:
        raw = pd.read_csv(path, dtype={date_column: str})
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise DatasetLoadError(f"{path.name} could not be parsed: {exc}", path=path) from exc

    expected = [date_column, *value_columns]
    if exact_columns and list(raw.columns) != expected:
        raise DatasetLoadError(
            f"{path.name}: columns {list(raw.columns)} do not match expected {expected}", path=path
        )
    missing = [c for c in expected if c not in raw.columns]
    if missing:
        raise DatasetLoadError(f"{path.name}: missing columns {missing}", path=path)

    dates = pd.to_datetime(raw[date_column], format="%Y-%m-%d", errors="coerce")
    if dates.isna().any():
        bad = raw.loc[dates.isna(), date_column].head(3).tolist()
        raise DatasetLoadError(f"{path.name}: malformed dates {bad}", path=path)
    frame = raw[list(value_columns)].copy()
    for col in value_columns:
        if not pd.api.types.is_numeric_dtype(frame[col]):
            raise DatasetLoadError(f"{path.name}: column {col!r} is not numeric", path=path)
        frame[col] = frame[col].astype("float64")
    frame.index = pd.DatetimeIndex(dates, name=date_column)
    if frame.index.has_duplicates:
        raise DatasetLoadError(f"{path.name}: duplicate dates", path=path)
    if not frame.index.is_monotonic_increasing:
        raise DatasetLoadError(f"{path.name}: dates are not sorted", path=path)
    return frame


def require_complete(frame: pd.DataFrame, name: str) -> None:
    if frame.isna().any().any():
        cols = frame.columns[frame.isna().any()].tolist()
        raise DatasetLoadError(f"{name}: missing values in {cols}")
    if not np.isfinite(frame.to_numpy()).all():
        raise DatasetLoadError(f"{name}: non-finite values")


def require_positive_prices(frame: pd.DataFrame, name: str) -> None:
    require_complete(frame, name)
    if (frame.to_numpy() <= 0).any():
        cols = frame.columns[(frame <= 0).any()].tolist()
        raise DatasetLoadError(f"{name}: non-positive prices in {cols}")
