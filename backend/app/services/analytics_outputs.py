"""Persistence of Phase 3 analytics outputs under data/processed/.

Only new files are written; Phase 2 artifacts (raw data, aligned tables, manifest,
reports) are never modified. A Phase 2 pipeline run deletes these derived files
because they would be stale; rerun ``scripts.run_analytics`` afterwards.
"""

import json
from pathlib import Path

import pandas as pd

from app.services.analytics_service import AnalyticsResult, statistics_frame, summary_document

OUTPUTS = {
    "asset_daily_returns": "returns/asset_daily_returns.csv",
    "benchmark_daily_returns": "returns/benchmark_daily_returns.csv",
    "descriptive_statistics": "metadata/descriptive_statistics.csv",
    "correlation_matrix": "metadata/correlation_matrix.csv",
    "daily_covariance_matrix": "metadata/daily_covariance_matrix.csv",
    "annualized_covariance_matrix": "metadata/annualized_covariance_matrix.csv",
    "analytics_summary": "metadata/analytics_summary.json",
}


def write_analytics_outputs(result: AnalyticsResult, data_dir: Path) -> dict[str, str]:
    processed = data_dir / "processed"
    paths = {k: processed / v for k, v in OUTPUTS.items()}
    rel = {k: p.relative_to(data_dir.parent).as_posix() for k, p in paths.items()}

    def csv(df: pd.DataFrame, key: str, index_label: str) -> None:
        paths[key].parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(paths[key], index_label=index_label, date_format="%Y-%m-%d", lineterminator="\n")

    csv(result.asset_returns, "asset_daily_returns", "date")
    csv(result.benchmark_returns, "benchmark_daily_returns", "date")
    stats = pd.concat(
        [
            statistics_frame(result.statistics_common, "common"),
            statistics_frame(result.statistics_individual, "individual"),
        ],
        ignore_index=True,
    )
    paths["descriptive_statistics"].parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(paths["descriptive_statistics"], index=False, lineterminator="\n")
    csv(result.correlation, "correlation_matrix", "asset_id")
    csv(result.covariance_daily, "daily_covariance_matrix", "asset_id")
    csv(result.covariance_annualized, "annualized_covariance_matrix", "asset_id")
    paths["analytics_summary"].write_text(
        json.dumps(summary_document(result, rel), indent=2, default=str) + "\n", encoding="utf-8"
    )
    return rel
