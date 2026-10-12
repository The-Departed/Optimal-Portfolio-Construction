import json
from pathlib import Path

import pandas as pd
import pytest

from app.core.config import Settings
from app.data.loader import ProcessedDataLoader
from app.data.validation import DatasetLoadError, read_dated_csv, require_positive_prices
from app.domain.assets import ASSET_IDS


def _csv(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "x.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_valid_file(tmp_path: Path) -> None:
    df = read_dated_csv(
        _csv(tmp_path, "date,A\n2024-01-01,1.5\n2024-01-02,2\n"),
        date_column="date",
        value_columns=("A",),
    )
    assert df.index.dtype.kind == "M" and df["A"].dtype == "float64"


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("date,B\n2024-01-01,1\n", "do not match"),
        ("date,A\n01/02/2024,1\n", "malformed dates"),
        ("date,A\n2024-01-02,1\n2024-01-01,2\n", "not sorted"),
        ("date,A\n2024-01-01,1\n2024-01-01,2\n", "duplicate"),
        ("date,A\n2024-01-01,abc\n", "not numeric"),
    ],
)
def test_schema_violations(tmp_path: Path, text: str, match: str) -> None:
    with pytest.raises(DatasetLoadError, match=match):
        read_dated_csv(_csv(tmp_path, text), date_column="date", value_columns=("A",))


def test_missing_file_message_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(DatasetLoadError, match="download_datasets"):
        read_dated_csv(tmp_path / "nope.csv", date_column="date", value_columns=("A",))


def test_non_positive_prices_rejected() -> None:
    frame = pd.DataFrame({"A": [1.0, 0.0]}, index=pd.bdate_range("2024-01-01", periods=2))
    with pytest.raises(DatasetLoadError, match="non-positive"):
        require_positive_prices(frame, "prices")


def test_loads_validated_synthetic_dataset(analytics_settings: Settings) -> None:
    ds = ProcessedDataLoader(analytics_settings.data_dir).load()
    assert ds.asset_ids == ASSET_IDS
    assert ds.portfolio_prices.index.equals(ds.benchmark_prices.index)
    assert ds.series_info["GSEC"].value_kind == "nav"
    assert ds.series_info["RF_TBILL_91D"].value_kind == "yield"
    assert len(ds.risk_free) > 0


def test_missing_manifest_and_blocked_dataset(data_dir: Path) -> None:
    with pytest.raises(DatasetLoadError, match="run the data pipeline"):
        ProcessedDataLoader(data_dir).load()


def test_corrupted_processed_file_is_detected(analytics_settings: Settings) -> None:
    path = analytics_settings.processed_dir / "prices" / "portfolio_prices_aligned.csv"
    df = pd.read_csv(path)
    df.drop(columns=["GOLD"]).to_csv(path, index=False)
    with pytest.raises(DatasetLoadError, match="columns"):
        ProcessedDataLoader(analytics_settings.data_dir).load()


def test_blocked_dataset_is_not_loaded(analytics_settings: Settings) -> None:
    manifest = analytics_settings.processed_dir / "manifest.json"
    data = json.loads(manifest.read_text())
    data["validation_passed"] = False
    manifest.write_text(json.dumps(data))
    with pytest.raises(DatasetLoadError, match="not passed"):
        ProcessedDataLoader(analytics_settings.data_dir).load()
