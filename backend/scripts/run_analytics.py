"""Compute and persist Phase 3 descriptive analytics. Run from backend/:

    uv run python -m scripts.run_analytics

Exit codes: 0 = PASS / PASS_WITH_WARNINGS, 1 = data not ready or analytics FAILED.
"""

import sys

from app.core.config import get_settings
from app.core.errors import DataNotReadyError
from app.services.analytics_service import AnalyticsService, AnalyticsStatus, persist


def main() -> int:
    settings = get_settings()
    try:
        result = AnalyticsService(settings).result()
    except DataNotReadyError as exc:
        print(f"Analytics unavailable: {exc.message}", file=sys.stderr)
        return 1
    files = persist(result, settings.data_dir)
    print(
        f"Sample: {result.sample_start} .. {result.sample_end} "
        f"({len(result.asset_returns)} daily returns)"
    )
    print(f"{'Series':<12}{'Obs':>6}{'CAGR':>10}{'Ann.vol':>10}{'Skew':>8}{'ExKurt':>8}")
    for s in result.statistics_common:
        print(
            f"{s.series_id:<12}{s.observations:>6}{s.annualized_return:>10.2%}"
            f"{s.annualized_volatility:>10.2%}{s.skewness:>8.2f}{s.excess_kurtosis:>8.2f}"
        )
    for c in result.checks:
        print(f"[{c.status:4}] {c.name}: {c.detail}")
    print("Outputs:", *files.values(), sep="\n  ")
    print(f"ANALYTICS STATUS: {result.status}")
    return 1 if result.status == AnalyticsStatus.FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
