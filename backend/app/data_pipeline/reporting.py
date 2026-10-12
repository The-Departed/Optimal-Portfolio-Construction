"""Write interim/processed datasets, machine-readable reports and the Markdown report."""

import json
from datetime import UTC
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import Settings
from app.data_pipeline import PIPELINE_VERSION, SCHEMA_VERSION
from app.data_pipeline.config import QualityThresholds
from app.data_pipeline.pipeline import DatasetResult, PipelineResult, RetrievalStatus
from app.data_pipeline.quality_checks import CheckStatus, DatasetStatus
from app.data_pipeline.source_registry import (
    BENCHMARK_DATASET,
    PORTFOLIO_DATASETS,
    RISK_FREE_DATASET,
    DatasetRole,
    ValueKind,
)

MANIFEST = "manifest.json"
REPORT_FILES = {
    "data_quality_report": "data_quality_report.md",
    "coverage_report": "coverage_report.csv",
    "missing_values_report": "missing_values_report.csv",
    "excluded_records": "excluded_records.csv",
    "extreme_returns_report": "extreme_returns_report.csv",
    "cross_source_report": "cross_source_report.csv",
    "source_manifest": "source_manifest.json",
    "validation_summary": "validation_summary.json",
}


def value_column(field_name: str) -> str:
    return {
        "Adj Close": "adj_close",
        "Close": "close",
        "Net Asset Value": "nav",
        "Implicit Yield at Cut-off Price (percent)": "implicit_yield_pct",
    }.get(field_name, field_name.lower().replace(" ", "_"))


def _rel(path: Path, settings: Settings) -> str:
    try:
        return path.relative_to(settings.data_dir.parent).as_posix()
    except ValueError:
        return str(path)


def _iso(ts: Any) -> str | None:
    return None if ts is None or pd.isna(ts) else pd.Timestamp(ts).date().isoformat()


def _write_csv(df: pd.DataFrame, path: Path, *, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, date_format="%Y-%m-%d", lineterminator="\n")


def _write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def _usable(res: DatasetResult) -> bool:
    return res.status in (DatasetStatus.PASS, DatasetStatus.PASS_WITH_WARNINGS)


# ------------------------------------------------------------------------- datasets


def _write_datasets(result: PipelineResult, s: Settings) -> dict[str, str]:
    files: dict[str, str] = {}
    for ds_id, res in result.datasets.items():
        spec = res.spec
        if res.snapshot is not None and res.snapshot.directory is not None:
            res.paths["raw"] = _rel(res.snapshot.directory, s)
        if res.records is None:
            continue
        sub = "risk_free" if spec.value_kind is ValueKind.YIELD else "prices"
        interim = s.interim_dir / sub / f"{ds_id}.csv"
        _write_csv(res.records, interim)
        res.paths["interim"] = _rel(interim, s)

        if spec.role is DatasetRole.CROSS_CHECK or not _usable(res):
            continue
        col = value_column(spec.source.value_field)
        if spec.value_kind is ValueKind.YIELD and res.rf_scope is not None:
            scope = res.rf_scope
            out = pd.DataFrame(
                {
                    "auction_date": scope["date"],
                    "issue_date": scope["issue_date"],
                    col: scope["value"],
                    "cut_off_price": scope["cut_off_price"],
                    "in_study_period": scope["date"] >= pd.Timestamp(result.study_start),
                    "handbook_edition": scope["edition_year"],
                    "rbi_page_id": scope["page_id"],
                }
            )
            path = s.processed_dir / "risk_free" / f"{ds_id}.csv"
            _write_csv(out, path)
            res.paths["processed"] = _rel(path, s)
            files[f"risk_free/{ds_id}"] = res.paths["processed"]
            continue
        if res.series is None:
            continue
        prices = res.series.rename(col).to_frame()
        prices.index.name = "date"
        p_path = s.processed_dir / "prices" / f"{ds_id}.csv"
        _write_csv(prices, p_path, index=True)
        res.paths["processed"] = _rel(p_path, s)
        files[f"prices/{ds_id}"] = res.paths["processed"]
        if res.native_returns is not None:
            r_path = s.processed_dir / "returns" / f"{ds_id}.csv"
            _write_csv(
                res.native_returns[["simple_return", "sessions_spanned"]], r_path, index=True
            )
            res.paths["processed_returns"] = _rel(r_path, s)
            files[f"returns/{ds_id}"] = res.paths["processed_returns"]
    return files


def _write_aligned(result: PipelineResult, s: Settings) -> dict[str, str]:
    a = result.aligned
    if a is None or result.alignment_error:
        return {}
    targets = {
        "portfolio_prices_aligned": (
            a.portfolio_prices,
            s.processed_dir / "prices" / "portfolio_prices_aligned.csv",
        ),
        "benchmark_prices_aligned": (
            a.benchmark_prices,
            s.processed_dir / "prices" / "benchmark_prices_aligned.csv",
        ),
        "portfolio_returns_aligned": (
            a.portfolio_returns,
            s.processed_dir / "returns" / "portfolio_returns_aligned.csv",
        ),
        "benchmark_returns_aligned": (
            a.benchmark_returns,
            s.processed_dir / "returns" / "benchmark_returns_aligned.csv",
        ),
    }
    files = {}
    for key, (df, path) in targets.items():
        _write_csv(df, path, index=True)
        files[key] = _rel(path, s)
    intervals = a.sessions_spanned.to_frame()
    intervals.index.name = "date"
    path = s.processed_dir / "metadata" / "return_intervals.csv"
    _write_csv(intervals, path, index=True)
    files["return_intervals"] = _rel(path, s)
    path = s.processed_dir / "metadata" / "alignment.json"
    _write_json(alignment_summary(result), path)
    files["alignment"] = _rel(path, s)
    return files


def alignment_summary(result: PipelineResult) -> dict[str, Any]:
    a = result.aligned
    cal = result.calendar
    if a is None:
        return {"status": "not_aligned", "error": result.alignment_error}
    common = a.common_dates
    multi = a.multi_session_returns
    return {
        "status": "aligned" if not result.alignment_error else "below_threshold",
        "error": result.alignment_error,
        "method": "Inner join on dates present in all eight portfolio assets and NIFTY 50; "
        "no filling. Returns computed on aligned prices; the first date has no return.",
        "asset_order": [d.dataset_id for d in PORTFOLIO_DATASETS],
        "benchmark": BENCHMARK_DATASET.dataset_id,
        "reference_calendar": {
            "definition": "Union of trading dates in the six NSE equity series",
            "first": _iso(cal[0]) if len(cal) else None,
            "last": _iso(cal[-1]) if len(cal) else None,
            "sessions": len(cal),
        },
        "common_period": {
            "first": _iso(common[0]),
            "last": _iso(common[-1]),
            "price_dates": len(common),
            "return_observations": len(a.portfolio_returns),
            "session_coverage": len(common) / len(cal) if len(cal) else None,
        },
        "sessions_dropped": sorted(_iso(d) for d in cal.difference(common)),
        "sessions_dropped_by_dataset": {
            k: [_iso(d) for d in v] for k, v in a.excluded_sessions.items() if v
        },
        "multi_session_returns": {_iso(d): int(n) for d, n in multi.items()},
        "calendar_findings": result.calendar_findings,
    }


# -------------------------------------------------------------------------- reports


def _common_coverage(res: DatasetResult, result: PipelineResult) -> float | None:
    if result.aligned is None or res.series is None or not len(res.series):
        return None
    return len(res.series.index.intersection(result.aligned.common_dates)) / len(res.series)


def coverage_rows(result: PipelineResult) -> list[dict[str, Any]]:
    rows = []
    for ds_id, res in result.datasets.items():
        cov, miss = res.quality.coverage, res.quality.missing
        notes = res.quality.messages(CheckStatus.FAIL) + res.quality.messages(CheckStatus.WARN)
        if res.retrieval_error:
            notes.insert(0, res.retrieval_error)
        rows.append(
            {
                "dataset_id": ds_id,
                "name": res.spec.name,
                "role": res.spec.role.value,
                "source": res.spec.source.source_name,
                "identifier": res.spec.source.identifier,
                "frequency": res.spec.frequency,
                "requested_start": result.study_start.isoformat(),
                "requested_end": result.study_end.isoformat(),
                "earliest_date": cov.get("first_date"),
                "latest_date": cov.get("last_date"),
                "observations": cov.get("observations"),
                "unique_dates": cov.get("unique_dates"),
                "missing_values": miss.get("missing_value"),
                "duplicate_dates": miss.get("duplicate_dates"),
                "excluded_records": miss.get("excluded_total"),
                "missing_sessions": cov.get("sessions_missing"),
                "target_period_coverage": cov.get("session_coverage"),
                "covers_target_period": cov.get("covers_target_period"),
                "common_period_coverage": _common_coverage(res, result),
                "longest_gap": cov.get(
                    "longest_missing_session_run", cov.get("longest_calendar_gap_days")
                ),
                "validation_status": res.status.value,
                "notes": " | ".join(notes),
            }
        )
    return rows


def _missing_rows(result: PipelineResult) -> list[dict[str, Any]]:
    rows = []
    for ds_id, res in result.datasets.items():
        m = res.quality.missing
        if not m:
            rows.append({"dataset_id": ds_id, "records": 0, "notes": res.retrieval_error or ""})
            continue
        by_reason = m.get("excluded_by_reason", {})
        rows.append(
            {
                "dataset_id": ds_id,
                "records": m["records"],
                "missing_values_before_cleaning": m["missing_value"],
                "missing_values_pct": round(m["missing_value_pct"], 4),
                "non_numeric": m["non_numeric"],
                "non_finite": m["non_finite"],
                "invalid_dates": m["invalid_date"],
                "non_positive_or_out_of_range": by_reason.get("non_positive", 0)
                + by_reason.get("out_of_range", 0),
                "duplicate_dates": m["duplicate_dates"],
                "source_errors": by_reason.get("source_error", 0),
                "excluded_total": m["excluded_total"],
                "valid_records_after_cleaning": m["valid_records"],
                "missing_values_after_cleaning": 0,
                "missing_sessions_vs_calendar": m.get("missing_sessions"),
                "missing_sessions_pct": None
                if m.get("missing_sessions_pct") is None
                else round(m["missing_sessions_pct"], 4),
                "notes": "; ".join(f"{k}={v}" for k, v in by_reason.items()),
            }
        )
    return rows


def _excluded_records(result: PipelineResult) -> pd.DataFrame:
    frames = []
    for ds_id, res in result.datasets.items():
        if res.records is None:
            continue
        ex = res.records[res.records["excluded"]]
        if ex.empty:
            continue
        cols = [
            c
            for c in (
                "date",
                "source_timestamp",
                "raw_value",
                "value",
                "exclusion_reason",
                "reference_value",
                "reference_deviation",
                "source_file",
            )
            if c in ex.columns
        ]
        frame = ex[cols].copy()
        frame.insert(0, "dataset_id", ds_id)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["dataset_id", "date", "raw_value", "exclusion_reason"])
    return pd.concat(frames, ignore_index=True)


def _extreme_returns(result: PipelineResult) -> pd.DataFrame:
    frames = []
    for ds_id, res in result.datasets.items():
        ext = res.quality.extreme_returns
        if ext is None or ext.empty:
            continue
        frame = ext.reset_index()
        frame.insert(0, "dataset_id", ds_id)
        frame["action"] = "flagged for investigation; retained"
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["dataset_id", "date", "simple_return"])
    return pd.concat(frames, ignore_index=True)


def _source_manifest(result: PipelineResult) -> dict[str, Any]:
    entries = []
    for ds_id, res in result.datasets.items():
        spec, snap = res.spec, res.snapshot
        entries.append(
            {
                "dataset_id": ds_id,
                "name": spec.name,
                "role": spec.role.value,
                "asset_class": spec.asset_class,
                "sector": spec.sector,
                "identifier": spec.source.identifier,
                "identifier_details": spec.source.params,
                "source_name": spec.source.source_name,
                "source_url": spec.source.url,
                "source_pages": (snap.source_metadata.get("editions") if snap else None),
                "retrieved_at": snap.retrieved_at.astimezone(UTC).isoformat() if snap else None,
                "retrieval_status": res.retrieval_status,
                "retrieval_error": res.retrieval_error,
                "requested_range": {
                    "start": result.study_start.isoformat(),
                    "end": result.study_end.isoformat(),
                },
                "actual_range": {
                    "start": res.quality.coverage.get("first_date"),
                    "end": res.quality.coverage.get("last_date"),
                },
                "frequency": spec.frequency,
                "selected_field": spec.source.value_field,
                "value_kind": spec.value_kind.value,
                "currency": spec.currency,
                "units": spec.units,
                "corporate_action_adjustment": spec.adjustment,
                "corporate_actions": [
                    {
                        "kind": a.kind,
                        "effective_date": a.effective_date.isoformat(),
                        "ratio": a.ratio,
                        "description": a.description,
                    }
                    for a in spec.corporate_actions
                ],
                "source_reported": (
                    snap.source_metadata
                    if snap and spec.source.kind.value == "yahoo_finance"
                    else None
                ),
                "files": res.paths,
                "validation_status": res.status.value,
                "known_limitations": list(spec.known_limitations),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": result.generated_at.isoformat(),
        "datasets": entries,
    }


def validation_summary(result: PipelineResult, t: QualityThresholds) -> dict[str, Any]:
    datasets = {}
    for ds_id, res in result.datasets.items():
        cov = res.quality.coverage
        datasets[ds_id] = {
            "name": res.spec.name,
            "role": res.spec.role.value,
            "critical": res.spec.critical,
            "status": res.status.value,
            "retrieval_status": res.retrieval_status,
            "source": res.spec.source.source_name,
            "identifier": res.spec.source.identifier,
            "frequency": res.spec.frequency,
            "units": res.spec.units,
            "first_date": cov.get("first_date"),
            "last_date": cov.get("last_date"),
            "observations": cov.get("observations"),
            "session_coverage": cov.get("session_coverage"),
            "checks": [
                {"name": c.name, "status": c.status.value, "detail": c.detail}
                for c in res.quality.checks
            ],
            "known_limitations": list(res.spec.known_limitations),
        }
    align = alignment_summary(result)
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": result.generated_at.isoformat(),
        "overall_status": result.overall.value,
        "ready_for_phase_3": result.ready,
        "study_period": {
            "start": result.study_start.isoformat(),
            "end": result.study_end.isoformat(),
        },
        "common_period": align.get("common_period"),
        "critical_failures": result.critical_failures,
        "warnings": result.warnings,
        "known_limitations": result.limitations,
        "calendar_findings": result.calendar_findings,
        "thresholds": {k: getattr(t, k) for k in t.__dataclass_fields__},
        "datasets": datasets,
    }


def write_outputs(result: PipelineResult, s: Settings, t: QualityThresholds) -> None:
    files = _write_datasets(result, s)
    files.update(_write_aligned(result, s))

    datasets_meta = s.processed_dir / "metadata" / "datasets.json"
    _write_json(_source_manifest(result)["datasets"], datasets_meta)
    files["datasets_metadata"] = _rel(datasets_meta, s)

    r = s.reports_dir
    _write_csv(pd.DataFrame(coverage_rows(result)), r / REPORT_FILES["coverage_report"])
    _write_csv(pd.DataFrame(_missing_rows(result)), r / REPORT_FILES["missing_values_report"])
    _write_csv(_excluded_records(result), r / REPORT_FILES["excluded_records"])
    _write_csv(_extreme_returns(result), r / REPORT_FILES["extreme_returns_report"])
    _write_csv(pd.DataFrame(result.cross_checks), r / REPORT_FILES["cross_source_report"])
    _write_json(_source_manifest(result), r / REPORT_FILES["source_manifest"])
    summary = validation_summary(result, t)
    _write_json(summary, r / REPORT_FILES["validation_summary"])

    from app.data_pipeline.markdown_report import render_report

    (r / REPORT_FILES["data_quality_report"]).write_text(
        render_report(result, summary), encoding="utf-8"
    )
    reports = {k: _rel(r / v, s) for k, v in REPORT_FILES.items()}

    result.files = files
    # The manifest is written last: its presence signals a complete run.
    _write_json(
        {
            "schema_version": SCHEMA_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "generated_at": result.generated_at.isoformat(),
            "validation_passed": result.ready,
            "overall_status": result.overall.value,
            "study_period": summary["study_period"],
            "common_period": summary["common_period"],
            "files": files,
            "reports": reports,
            "risk_free_dataset": RISK_FREE_DATASET.dataset_id,
            "retrieval": {k: v.retrieval_status for k, v in result.datasets.items()},
            "downloaded_this_run": [
                k
                for k, v in result.datasets.items()
                if v.retrieval_status == RetrievalStatus.DOWNLOADED
            ],
        },
        s.processed_dir / MANIFEST,
    )
