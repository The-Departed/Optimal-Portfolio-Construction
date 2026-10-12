"""Primary-vs-secondary source comparisons.

Two different price definitions (exchange close vs NAV, adjusted vs unadjusted) are
not expected to match exactly; the comparison quantifies the difference.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.data_pipeline.returns import simple_returns


def compare_series(
    primary: pd.Series,
    reference: pd.Series,
    *,
    primary_label: str,
    reference_label: str,
    excluded_source_errors: int = 0,
    expected_causes: str = "",
) -> dict[str, Any]:
    common = primary.index.intersection(reference.index).sort_values()
    p, r = primary.reindex(common), reference.reindex(common)
    dev = p / r - 1.0
    abs_dev = dev.abs()
    rp, rr = simple_returns(p), simple_returns(r)
    diff = rp - rr
    worst = abs_dev.idxmax() if len(abs_dev) else None
    return {
        "primary": primary_label,
        "reference": reference_label,
        "matched_dates": len(common),
        "primary_only_dates": len(primary.index.difference(reference.index)),
        "reference_only_dates": len(reference.index.difference(primary.index)),
        "median_abs_level_deviation": float(abs_dev.median()) if len(common) else None,
        "p95_abs_level_deviation": float(abs_dev.quantile(0.95)) if len(common) else None,
        "max_abs_level_deviation": float(abs_dev.max()) if len(common) else None,
        "max_deviation_date": worst.date().isoformat() if worst is not None else None,
        "days_over_1pct": int((abs_dev > 0.01).sum()),
        "days_over_5pct": int((abs_dev > 0.05).sum()),
        "return_correlation": float(np.corrcoef(rp, rr)[0, 1]) if len(rp) > 2 else None,
        "return_difference_std": float(diff.std()) if len(diff) > 2 else None,
        "excluded_source_errors": excluded_source_errors,
        "expected_causes": expected_causes,
    }
