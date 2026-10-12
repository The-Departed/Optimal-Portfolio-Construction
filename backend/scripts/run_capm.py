"""Estimate CAPM for the six equities and persist the results. Run from backend/:

    uv run python -m scripts.run_capm

Writes data/processed/metadata/capm_results.csv and capm_summary.json.
Exit codes: 0 = all regressions estimated, 1 = data unavailable or a regression failed.
"""

import json
import sys

import pandas as pd

from app.core.config import get_settings
from app.core.errors import DataNotReadyError
from app.services.capm_service import CapmService


def main() -> int:
    settings = get_settings()
    try:
        summary = CapmService(settings).summary()
    except DataNotReadyError as exc:
        print(f"CAPM unavailable: {exc.message}", file=sys.stderr)
        return 1
    out = settings.processed_dir / "metadata"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for e in summary.equities:
        row = e.model_dump(exclude={"diagnostics", "warnings"})
        row.update(e.diagnostics.model_dump() if e.diagnostics else {})
        row["warnings"] = "; ".join(e.warnings)
        rows.append(row)
    pd.DataFrame(rows).to_csv(out / "capm_results.csv", index=False, lineterminator="\n")
    (out / "capm_summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )
    print(f"Sample {summary.sample_start} .. {summary.sample_end} ({summary.observations} returns)")
    print(
        f"R_f (annualized) {summary.risk_free.annualized_rate:.2%}  "
        f"E(R_m) {summary.market.mean_return:.2%}"
    )
    print(f"{'Equity':<12}{'Beta':>7}{'R2':>7}{'Hist':>9}{'CAPM':>9}{'Alpha':>9}")
    for e in summary.equities:
        if e.status != "ok":
            print(f"{e.asset_id:<12} FAILED: {e.error}")
            continue
        print(
            f"{e.asset_id:<12}{e.beta:>7.3f}{e.r_squared:>7.3f}{e.historical_mean_return:>9.2%}"
            f"{e.capm_expected_return:>9.2%}{e.jensens_alpha:>9.2%}"
        )
    print(f"CAPM STATUS: {summary.status}")
    return 1 if summary.status == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
