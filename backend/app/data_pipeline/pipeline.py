"""Pipeline orchestration: acquire -> normalize -> clean -> validate -> align -> write."""

import logging
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import Settings
from app.data_pipeline import cleaning
from app.data_pipeline.alignment import AlignedData, align, reference_calendar
from app.data_pipeline.config import DEFAULT_THRESHOLDS, QualityThresholds
from app.data_pipeline.cross_source import compare_series
from app.data_pipeline.downloaders import DEFAULT_DOWNLOADERS, Downloader
from app.data_pipeline.downloaders.base import DownloadContext, DownloadError
from app.data_pipeline.normalization import normalize
from app.data_pipeline.quality_checks import (
    CheckStatus,
    DatasetQuality,
    DatasetStatus,
    OverallStatus,
    check_calendar_reference,
    check_daily_coverage,
    check_identity,
    check_returns,
    check_risk_free,
    overall_status,
    summarize_records,
)
from app.data_pipeline.raw_store import RawSnapshot, RawStore
from app.data_pipeline.source_registry import (
    BENCHMARK_DATASET,
    DATASETS,
    EQUITY_DATASET_IDS,
    PORTFOLIO_DATASETS,
    DatasetRole,
    DatasetSpec,
    ValueKind,
)

log = logging.getLogger(__name__)


class RetrievalStatus:
    DOWNLOADED = "downloaded"
    CACHED = "cached"
    FAILED = "failed"


@dataclass
class DatasetResult:
    spec: DatasetSpec
    retrieval_status: str
    retrieval_error: str | None = None
    snapshot: RawSnapshot | None = None
    records: pd.DataFrame | None = None
    series: pd.Series | None = None
    native_returns: pd.DataFrame | None = None
    rf_scope: pd.DataFrame | None = None
    quality: DatasetQuality = field(default_factory=lambda: DatasetQuality(""))
    paths: dict[str, str] = field(default_factory=dict)

    @property
    def status(self) -> DatasetStatus:
        return self.quality.status


@dataclass
class PipelineResult:
    generated_at: datetime
    study_start: date
    study_end: date
    datasets: dict[str, DatasetResult]
    calendar: pd.DatetimeIndex
    aligned: AlignedData | None
    alignment_error: str | None
    cross_checks: list[dict[str, Any]]
    overall: OverallStatus
    critical_failures: list[str]
    warnings: list[str]
    limitations: list[str]
    files: dict[str, str] = field(default_factory=dict)
    calendar_findings: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.overall is not OverallStatus.BLOCKED


@dataclass
class PipelineOptions:
    refresh: bool = False
    offline: bool = False


class DataPipeline:
    def __init__(
        self,
        settings: Settings,
        *,
        datasets: tuple[DatasetSpec, ...] = DATASETS,
        downloaders: Mapping[Any, Downloader] | None = None,
        thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
        clock: Any = None,
    ) -> None:
        self.settings = settings
        self.specs = {d.dataset_id: d for d in datasets}
        self.downloaders = dict(downloaders or DEFAULT_DOWNLOADERS)
        self.t = thresholds
        self.raw_store = RawStore(settings.raw_dir)
        self._clock = clock or (lambda: datetime.now(UTC).replace(microsecond=0))

    # ---------------------------------------------------------------- acquisition
    def _acquire(
        self, spec: DatasetSpec, ctx: DownloadContext, opts: PipelineOptions
    ) -> DatasetResult:
        cached = None if opts.refresh else self.raw_store.latest(spec)
        if cached is not None:
            log.info("%-14s using cached raw snapshot %s", spec.dataset_id, cached.directory.name)
            return DatasetResult(spec, RetrievalStatus.CACHED, snapshot=cached)
        if opts.offline:
            return DatasetResult(
                spec, RetrievalStatus.FAILED, "No cached raw snapshot (offline mode)"
            )
        downloader = self.downloaders.get(spec.source.kind)
        if downloader is None:
            return DatasetResult(
                spec, RetrievalStatus.FAILED, f"No downloader for {spec.source.kind}"
            )
        try:
            snapshot = downloader(spec, ctx)
        except DownloadError as exc:
            log.error("%-14s download FAILED: %s", spec.dataset_id, exc)
            return DatasetResult(spec, RetrievalStatus.FAILED, str(exc))
        self.raw_store.save(spec, snapshot)
        log.info("%-14s downloaded -> %s", spec.dataset_id, snapshot.directory)
        return DatasetResult(spec, RetrievalStatus.DOWNLOADED, snapshot=snapshot)

    # ------------------------------------------------------------------- cleaning
    def _clean(self, res: DatasetResult) -> None:
        spec = res.spec
        assert res.snapshot is not None
        try:
            df = normalize(spec, res.snapshot)
        except Exception as exc:  # malformed raw data must not crash the whole run
            res.retrieval_error = f"Raw data could not be parsed: {exc}"
            res.quality.add("parse", CheckStatus.FAIL, res.retrieval_error)
            return
        df = cleaning.apply_value_rules(df, spec, self.t)
        prefer = "edition_year" if spec.value_kind is ValueKind.YIELD else None
        res.records = cleaning.resolve_duplicates(df, prefer_column=prefer)
        res.quality.dataset_id = spec.dataset_id

    # ----------------------------------------------------------------------- run
    def run(self, opts: PipelineOptions | None = None) -> PipelineResult:
        opts = opts or PipelineOptions()
        s = self.settings
        generated_at = self._clock()
        self._reset_outputs()

        ctx = DownloadContext(
            start=s.study_start,
            end=s.study_end,
            timeout_seconds=s.http_timeout_seconds,
            pause_seconds=s.http_pause_seconds,
            user_agent=s.http_user_agent,
        )
        results: dict[str, DatasetResult] = {}
        for spec in self.specs.values():
            res = self._acquire(spec, ctx, opts)
            res.quality = DatasetQuality(spec.dataset_id, retrieved=res.snapshot is not None)
            if res.snapshot is not None:
                self._clean(res)
            results[spec.dataset_id] = res

        start, end = pd.Timestamp(s.study_start), pd.Timestamp(s.study_end)
        equity_series = {
            i: cleaning.valid_series(results[i].records)
            for i in EQUITY_DATASET_IDS
            if i in results and results[i].records is not None
        }
        calendar = reference_calendar(equity_series, start, end)
        holidays = self._holidays(results)

        cross_checks = self._cross_checks(results)
        for res in results.values():
            self._validate(res, calendar, holidays)
        calendar_findings = self._calendar_findings(results, calendar, holidays)

        aligned, alignment_error = self._align(results, calendar)
        result = self._finalize(
            results, calendar, aligned, alignment_error, cross_checks, generated_at
        )
        result.calendar_findings = calendar_findings
        if calendar_findings["probable_missing_sessions"]:
            result.warnings.append(
                "calendar: probable NSE sessions absent from every Yahoo series: "
                + ", ".join(calendar_findings["probable_missing_sessions"])
            )
            if result.overall is OverallStatus.PASS:
                result.overall = OverallStatus.PASS_WITH_WARNINGS

        from app.data_pipeline.reporting import write_outputs  # avoid import cycle

        write_outputs(result, s, self.t)
        return result

    # ------------------------------------------------------------ cross-checking
    def _cross_checks(self, results: dict[str, DatasetResult]) -> list[dict[str, Any]]:
        out = []
        for res in results.values():
            spec = res.spec
            ref_id = spec.reference_dataset
            if ref_id is None or res.records is None:
                continue
            ref = results.get(ref_id)
            if ref is None or ref.records is None:
                res.quality.add("cross_source", CheckStatus.WARN, f"Reference {ref_id} unavailable")
                continue
            ref_series = cleaning.valid_series(ref.records)
            if ref.spec.adjust_for_actions:
                ref_series = cleaning.split_adjusted(ref_series, ref.spec.corporate_actions)
            res.records = cleaning.flag_reference_deviation(
                res.records,
                ref_series,
                self.t.source_error_deviation,
                exclude=spec.exclude_on_reference_deviation,
            )
            errors = int((res.records["exclusion_reason"] == "source_error").sum())
            if errors:
                bad = res.records[res.records["exclusion_reason"] == "source_error"]
                res.quality.add(
                    "source_errors",
                    CheckStatus.WARN,
                    f"{errors} record(s) deviate >{self.t.source_error_deviation:.0%} from "
                    f"{ref_id} and were excluded: "
                    + ", ".join(
                        f"{d.date()} ({v:g} vs ref {r:g})"
                        for d, v, r in bad[["date", "value", "reference_value"]].itertuples(
                            index=False
                        )
                    ),
                )
            summary = compare_series(
                cleaning.valid_series(res.records),
                ref_series,
                primary_label=_label(spec),
                reference_label=_label(ref.spec),
                excluded_source_errors=errors,
                expected_causes=_EXPECTED_CAUSES.get(spec.dataset_id, ""),
            )
            summary["dataset_id"] = spec.dataset_id
            summary["reference_dataset_id"] = ref_id
            res.quality.add(
                "cross_source",
                CheckStatus.PASS,
                f"vs {ref_id}: median |dev| {summary['median_abs_level_deviation']:.3%}, "
                f"p95 {summary['p95_abs_level_deviation']:.3%}, return corr "
                f"{summary['return_correlation']:.3f}",
            )
            out.append(summary)
        return out

    # ---------------------------------------------------------------- validation
    def _holidays(self, results: dict[str, DatasetResult]) -> dict[pd.Timestamp, str] | None:
        res = next(
            (r for r in results.values() if r.spec.role is DatasetRole.CALENDAR_REFERENCE), None
        )
        if res is None or res.records is None:
            return None
        valid = res.records[~res.records["excluded"]]
        return {
            pd.Timestamp(d): str(name)
            for d, name in zip(valid["date"], valid["raw_value"], strict=True)
        }

    def _explained_sessions(
        self, calendar: pd.DatetimeIndex, holidays: dict[pd.Timestamp, str] | None
    ) -> dict[pd.Timestamp, str]:
        out: dict[pd.Timestamp, str] = {}
        for d in calendar:
            if d.dayofweek >= 5:
                out[d] = "weekend special NSE session: no NAV on non-business days"
            elif holidays and d in holidays:
                out[d] = f"RBI Mumbai bank holiday: {holidays[d]}"
        return out

    def _calendar_findings(
        self,
        results: dict[str, DatasetResult],
        calendar: pd.DatetimeIndex,
        holidays: dict[pd.Timestamp, str] | None,
    ) -> dict[str, Any]:
        """Weekdays absent from every Yahoo NSE series but evidenced as business days.

        Evidence: not an RBI Mumbai holiday and the AMFI gold-ETF NAV was struck.
        These are *probable* NSE sessions missing from the source, not proven ones.
        """
        nav = results.get("GOLD_NAV")
        if nav is None or nav.series is None or holidays is None or not len(calendar):
            return {"probable_missing_sessions": [], "evidence": "unavailable"}
        nav_dates = set(nav.series.index)
        cal = set(calendar)
        candidates = [
            d
            for d in pd.bdate_range(calendar[0], calendar[-1])
            if d not in cal and d not in holidays and d in nav_dates
        ]
        return {
            "probable_missing_sessions": [d.date().isoformat() for d in candidates],
            "evidence": "weekday, not an RBI Mumbai holiday, AMFI NAV published",
        }

    def _validate(
        self,
        res: DatasetResult,
        calendar: pd.DatetimeIndex,
        holidays: dict[pd.Timestamp, str] | None = None,
    ) -> None:
        if res.records is None:
            return
        spec, q, s = res.spec, res.quality, self.settings
        check_identity(q, spec, res.snapshot, res.records)
        summarize_records(q, res.records)
        if spec.value_kind is ValueKind.CALENDAR:
            check_calendar_reference(q, res.records, s.study_start, s.study_end)
            return
        if spec.value_kind is ValueKind.YIELD:
            res.rf_scope = check_risk_free(q, res.records, s.study_start, s.study_end, self.t)
            return
        series = cleaning.valid_series(res.records)
        if spec.adjust_for_actions and spec.corporate_actions:
            series = cleaning.split_adjusted(series, spec.corporate_actions)
            q.add(
                "corporate_actions",
                CheckStatus.PASS,
                "Unadjusted source expressed in post-action units for validation: "
                + "; ".join(
                    f"{a.kind} 1:{a.ratio:g} from {a.effective_date}"
                    for a in spec.corporate_actions
                ),
            )
        window = series[
            (series.index >= pd.Timestamp(s.study_start))
            & (series.index <= pd.Timestamp(s.study_end))
        ]
        res.series = window
        if len(calendar) == 0:
            q.add(
                "coverage", CheckStatus.FAIL, "Reference calendar unavailable (equity data missing)"
            )
            return
        explained = None
        if spec.nav_calendar:
            explained = self._explained_sessions(calendar, holidays)
            if holidays is None:
                q.add(
                    "holiday_evidence",
                    CheckStatus.WARN,
                    "RBI holiday list unavailable: only weekend sessions can be explained",
                )
        check_daily_coverage(q, window, calendar, s.study_start, s.study_end, self.t, explained)
        res.native_returns = check_returns(q, spec, window, calendar, self.t)

    # ----------------------------------------------------------------- alignment
    def _align(
        self, results: dict[str, DatasetResult], calendar: pd.DatetimeIndex
    ) -> tuple[AlignedData | None, str | None]:
        needed = [*PORTFOLIO_DATASETS, BENCHMARK_DATASET]
        unusable = [
            d.dataset_id
            for d in needed
            if results.get(d.dataset_id) is None
            or results[d.dataset_id].series is None
            or results[d.dataset_id].status in (DatasetStatus.FAIL, DatasetStatus.NOT_RETRIEVED)
        ]
        if unusable:
            return None, f"Alignment skipped: unusable dataset(s) {', '.join(unusable)}"
        try:
            aligned = align(
                {d.dataset_id: results[d.dataset_id].series for d in PORTFOLIO_DATASETS},
                (BENCHMARK_DATASET.dataset_id, results[BENCHMARK_DATASET.dataset_id].series),
                calendar,
            )
        except ValueError as exc:
            return None, str(exc)
        coverage = len(aligned.common_dates) / len(calendar)
        if coverage < self.t.min_common_session_coverage:
            return aligned, (
                f"Common sample covers {coverage:.2%} of reference sessions "
                f"(< {self.t.min_common_session_coverage:.0%})"
            )
        return aligned, None

    # ------------------------------------------------------------------ finalize
    def _finalize(
        self,
        results: dict[str, DatasetResult],
        calendar: pd.DatetimeIndex,
        aligned: AlignedData | None,
        alignment_error: str | None,
        cross_checks: list[dict[str, Any]],
        generated_at: datetime,
    ) -> PipelineResult:
        critical = {d.dataset_id for d in self.specs.values() if d.critical}
        statuses = {k: r.status for k, r in results.items()}
        failures, warnings = [], []
        for k, r in results.items():
            if r.status is DatasetStatus.NOT_RETRIEVED:
                msg = f"{k}: not retrieved ({r.retrieval_error})"
                (failures if k in critical else warnings).append(msg)
            for m in r.quality.messages(CheckStatus.FAIL):
                (failures if k in critical else warnings).append(f"{k}: {m}")
            warnings.extend(f"{k}: {m}" for m in r.quality.messages(CheckStatus.WARN))
        if alignment_error:
            failures.append(f"alignment: {alignment_error}")
        if aligned is not None and len(aligned.multi_session_returns):
            warnings.append(
                f"alignment: {len(aligned.multi_session_returns)} aligned return(s) span more "
                "than one reference session because a date was missing in at least one series"
            )
        limitations = sorted(
            {
                f"{d.dataset_id}: {lim}"
                for d in self.specs.values()
                if d.role is not DatasetRole.CROSS_CHECK
                for lim in d.known_limitations
            }
        )
        overall = overall_status(
            statuses,
            critical,
            alignment_ok=aligned is not None and alignment_error is None,
            has_warnings=bool(warnings or limitations),
        )
        return PipelineResult(
            generated_at=generated_at,
            study_start=self.settings.study_start,
            study_end=self.settings.study_end,
            datasets=results,
            calendar=calendar,
            aligned=aligned,
            alignment_error=alignment_error,
            cross_checks=cross_checks,
            overall=overall,
            critical_failures=failures,
            warnings=warnings,
            limitations=limitations,
        )

    def _reset_outputs(self) -> None:
        """Remove previously generated outputs so a failed run cannot leave stale data."""
        s = self.settings
        manifest = s.processed_dir / "manifest.json"
        manifest.unlink(missing_ok=True)
        for sub in (
            s.interim_dir / "prices",
            s.interim_dir / "risk_free",
            s.processed_dir / "prices",
            s.processed_dir / "returns",
            s.processed_dir / "risk_free",
            s.processed_dir / "metadata",
            # Derived Phase 4/5 outputs become stale when the dataset is rebuilt.
            s.processed_dir / "simulations",
        ):
            if sub.exists():
                shutil.rmtree(sub)
            sub.mkdir(parents=True)
        s.reports_dir.mkdir(parents=True, exist_ok=True)


_EXPECTED_CAUSES = {
    "GOLD": "Exchange close vs end-of-day NAV (timing, ETF premium/discount); NAV is "
    "split-adjusted here for comparison; Yahoo double-adjusted rows show as ~-99%.",
    "GSEC": "NAV vs illiquid exchange trades: stale last-traded prices, wide intraday "
    "prints and days without trades.",
}


def _label(spec: DatasetSpec) -> str:
    return f"{spec.dataset_id} ({spec.source.source_name}: {spec.source.value_field})"


def resolve_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)
