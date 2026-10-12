"""Loads the validated Phase 2 dataset for analytics.

Reads only artifacts referenced by ``data/processed/manifest.json``; never downloads or
modifies data. All loading and schema validation happens here, separate from the
financial calculations in ``app.analytics``.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.repository import DataRepository, ManifestError
from app.data.validation import (
    DatasetLoadError,
    read_dated_csv,
    require_complete,
    require_positive_prices,
)
from app.domain.assets import ASSET_IDS, BENCHMARK

RISK_FREE_ID = "RF_TBILL_91D"
_RF_COLUMNS = (
    "auction_date",
    "issue_date",
    "implicit_yield_pct",
    "cut_off_price",
    "in_study_period",
    "handbook_edition",
    "rbi_page_id",
)
_VALUE_COLUMN = {"price": "adj_close", "nav": "nav", "index_level": "close"}


@dataclass(frozen=True)
class SeriesInfo:
    dataset_id: str
    value_kind: str
    selected_field: str
    source_name: str
    identifier: str
    units: str
    frequency: str


@dataclass(frozen=True)
class ValidatedDataset:
    manifest_generated_at: str
    overall_status: str
    pipeline_version: str | None
    portfolio_prices: pd.DataFrame
    benchmark_prices: pd.DataFrame
    phase2_portfolio_returns: pd.DataFrame
    phase2_benchmark_returns: pd.DataFrame
    sessions_spanned: pd.Series
    individual_prices: dict[str, pd.Series]
    series_info: dict[str, SeriesInfo]
    risk_free: pd.DataFrame
    warnings: tuple[str, ...]
    known_limitations: tuple[str, ...]
    source_files: dict[str, str]

    @property
    def asset_ids(self) -> tuple[str, ...]:
        return tuple(self.portfolio_prices.columns)


class ProcessedDataLoader:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._repo = DataRepository(data_dir / "processed", data_dir / "reports")

    def _path(self, files: dict[str, str], key: str) -> Path:
        if key not in files:
            raise DatasetLoadError(
                f"Manifest does not reference '{key}'. Re-run the data pipeline."
            )
        return self._data_dir.parent / files[key]

    def load(self) -> ValidatedDataset:
        try:
            manifest = self._repo.load_manifest()
            summary = self._repo.load_validation_summary()
        except ManifestError as exc:
            raise DatasetLoadError(str(exc)) from exc
        if manifest is None:
            raise DatasetLoadError("No processed dataset: run the data pipeline first.")
        if not manifest.validation_passed or summary is None:
            raise DatasetLoadError("The processed dataset has not passed Phase 2 validation.")
        if summary.get("overall_status") != manifest.overall_status:
            raise DatasetLoadError("Manifest and validation summary disagree; re-run the pipeline.")
        files = manifest.files
        bench = BENCHMARK.id

        prices = read_dated_csv(
            self._path(files, "portfolio_prices_aligned"),
            date_column="date",
            value_columns=ASSET_IDS,
        )
        bench_prices = read_dated_csv(
            self._path(files, "benchmark_prices_aligned"),
            date_column="date",
            value_columns=(bench,),
        )
        p2_returns = read_dated_csv(
            self._path(files, "portfolio_returns_aligned"),
            date_column="date",
            value_columns=ASSET_IDS,
        )
        p2_bench_returns = read_dated_csv(
            self._path(files, "benchmark_returns_aligned"),
            date_column="date",
            value_columns=(bench,),
        )
        intervals = read_dated_csv(
            self._path(files, "return_intervals"),
            date_column="date",
            value_columns=("sessions_spanned",),
        )["sessions_spanned"]

        require_positive_prices(prices, "portfolio_prices_aligned")
        require_positive_prices(bench_prices, "benchmark_prices_aligned")
        require_complete(p2_returns, "portfolio_returns_aligned")
        require_complete(p2_bench_returns, "benchmark_returns_aligned")
        if not prices.index.equals(bench_prices.index):
            raise DatasetLoadError("Portfolio and benchmark price tables use different dates")
        if not p2_returns.index.equals(prices.index[1:]) or not p2_bench_returns.index.equals(
            prices.index[1:]
        ):
            raise DatasetLoadError("Return tables are not aligned with the common price dates")
        if not intervals.index.equals(p2_returns.index):
            raise DatasetLoadError("return_intervals does not match the return dates")

        info = self._series_info()
        individual = {}
        for ds_id in (*ASSET_IDS, bench):
            kind = info[ds_id].value_kind
            column = _VALUE_COLUMN.get(kind)
            if column is None:
                raise DatasetLoadError(
                    f"{ds_id}: unsupported value kind {kind!r} for a price series"
                )
            frame = read_dated_csv(
                self._path(files, f"prices/{ds_id}"), date_column="date", value_columns=(column,)
            )
            require_positive_prices(frame, f"prices/{ds_id}")
            individual[ds_id] = frame[column].rename(ds_id)

        rf = self._risk_free(self._path(files, f"risk_free/{RISK_FREE_ID}"))
        if info.get(RISK_FREE_ID) is None or info[RISK_FREE_ID].value_kind != "yield":
            raise DatasetLoadError(f"{RISK_FREE_ID} is not recorded as a yield series")

        return ValidatedDataset(
            manifest_generated_at=manifest.generated_at.isoformat(),
            overall_status=str(manifest.overall_status),
            pipeline_version=manifest.pipeline_version,
            portfolio_prices=prices,
            benchmark_prices=bench_prices,
            phase2_portfolio_returns=p2_returns,
            phase2_benchmark_returns=p2_bench_returns,
            sessions_spanned=intervals.astype(int),
            individual_prices=individual,
            series_info=info,
            risk_free=rf,
            warnings=tuple(summary.get("warnings", [])),
            known_limitations=tuple(summary.get("known_limitations", [])),
            source_files={k: v for k, v in files.items()},
        )

    def _series_info(self) -> dict[str, SeriesInfo]:
        path = self._data_dir / "reports" / "source_manifest.json"
        if not path.is_file():
            raise DatasetLoadError(
                "source_manifest.json is missing; re-run the data pipeline.", path=path
            )
        try:
            entries: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["datasets"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DatasetLoadError(f"source_manifest.json is invalid: {exc}", path=path) from exc
        out = {}
        for e in entries:
            try:
                out[e["dataset_id"]] = SeriesInfo(
                    dataset_id=e["dataset_id"],
                    value_kind=e["value_kind"],
                    selected_field=e["selected_field"],
                    source_name=e["source_name"],
                    identifier=str(e["identifier"]),
                    units=e["units"],
                    frequency=e["frequency"],
                )
            except KeyError as exc:
                raise DatasetLoadError(
                    f"source_manifest.json entry lacks {exc}", path=path
                ) from exc
        missing = [d for d in (*ASSET_IDS, BENCHMARK.id, RISK_FREE_ID) if d not in out]
        if missing:
            raise DatasetLoadError(f"source_manifest.json lacks datasets {missing}", path=path)
        return out

    @staticmethod
    def _risk_free(path: Path) -> pd.DataFrame:
        if not path.is_file():
            raise DatasetLoadError(f"Required file {path.name} is missing.", path=path)
        df = pd.read_csv(path)
        if tuple(df.columns) != _RF_COLUMNS:
            raise DatasetLoadError(f"{path.name}: unexpected columns {list(df.columns)}", path=path)
        df["auction_date"] = pd.to_datetime(df["auction_date"], format="%Y-%m-%d", errors="coerce")
        if df["auction_date"].isna().any():
            raise DatasetLoadError(f"{path.name}: malformed auction dates", path=path)
        if (
            not pd.api.types.is_numeric_dtype(df["implicit_yield_pct"])
            or df["implicit_yield_pct"].isna().any()
        ):
            raise DatasetLoadError(
                f"{path.name}: implicit_yield_pct must be numeric and complete", path=path
            )
        if df["auction_date"].duplicated().any() or not df["auction_date"].is_monotonic_increasing:
            raise DatasetLoadError(
                f"{path.name}: auction dates must be sorted and unique", path=path
            )
        return df
