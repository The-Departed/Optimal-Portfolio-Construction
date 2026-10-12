"""Command-line entry point: ``uv run python -m scripts.download_datasets``.

Exit codes: 0 = PASS or PASS_WITH_WARNINGS, 1 = BLOCKED (or warnings with
``--strict``), 2 = unexpected error.
"""

import argparse
import logging
import sys
from collections.abc import Callable

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.data_pipeline.pipeline import DataPipeline, PipelineOptions, PipelineResult
from app.data_pipeline.quality_checks import OverallStatus


def _summary(result: PipelineResult) -> str:
    lines = [
        "",
        f"{'Dataset':<21}{'Retrieval':<12}{'Status':<20}{'First':<12}{'Last':<12}{'Obs':>6}",
        "-" * 83,
    ]
    for ds_id, res in result.datasets.items():
        c = res.quality.coverage
        lines.append(
            f"{ds_id:<21}{res.retrieval_status:<12}{res.status.value:<20}"
            f"{c.get('first_date') or '-':<12}{c.get('last_date') or '-':<12}"
            f"{c.get('observations') or 0:>6}"
        )
    a = result.aligned
    if a is not None:
        lines.append(
            f"\nCommon sample: {a.common_dates[0].date()} .. {a.common_dates[-1].date()} "
            f"({len(a.common_dates)} dates, {len(a.portfolio_returns)} returns)"
        )
    for m in result.critical_failures:
        lines.append(f"CRITICAL  {m}")
    lines.append(f"\nWarnings: {len(result.warnings)}  (see data/reports/data_quality_report.md)")
    lines.append(f"OVERALL STATUS: {result.overall.value}")
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    pipeline_factory: Callable[[Settings], DataPipeline] = DataPipeline,
) -> int:
    parser = argparse.ArgumentParser(
        description="Acquire, clean and validate the project datasets."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--refresh",
        action="store_true",
        help="download new raw snapshots even if cached ones exist",
    )
    mode.add_argument(
        "--offline", action="store_true", help="never use the network; rebuild from cached raw data"
    )
    parser.add_argument("--strict", action="store_true", help="exit non-zero on PASS_WITH_WARNINGS")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)
    try:
        result = pipeline_factory(settings).run(
            PipelineOptions(refresh=args.refresh, offline=args.offline)
        )
    except Exception:
        logging.getLogger(__name__).exception("Pipeline crashed")
        return 2
    print(_summary(result))
    if result.overall is OverallStatus.BLOCKED:
        return 1
    if args.strict and result.overall is OverallStatus.PASS_WITH_WARNINGS:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
