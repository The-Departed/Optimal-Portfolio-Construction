"""Validation thresholds for the data pipeline.

These are data-quality rules, not financial-model parameters. Changing a threshold
changes which datasets pass validation, so changes must be documented in
docs/methodology.md and data/README.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QualityThresholds:
    # Daily series ---------------------------------------------------------------
    # Minimum share of reference trading sessions in the study period with a valid
    # observation. Below this a dataset fails.
    min_session_coverage: float = 0.98
    # Longest run of consecutive missing reference sessions tolerated.
    max_missing_session_run: int = 5
    # First/last observation may be at most this many calendar days inside the
    # study-period boundary.
    boundary_tolerance_days: int = 7
    # |simple return| above this is treated as a probable data discontinuity
    # (e.g. an unadjusted split) and fails validation unless explained.
    discontinuity_return: float = 0.5
    # Primary-vs-reference deviation above which a primary record is classified
    # as a source error (used only where a dataset opts in).
    source_error_deviation: float = 0.2

    # Risk-free (auction) series -------------------------------------------------
    # A gap between auctions above this is a warning...
    rf_gap_warning_days: int = 8
    # ...and above this a failure.
    rf_gap_failure_days: int = 35
    # Plausible range of an annualized T-bill yield, in percent.
    rf_min_yield_pct: float = 0.0
    rf_max_yield_pct: float = 20.0
    # Reported implicit yield vs yield recomputed from the cut-off price (pp).
    rf_price_yield_tolerance_pp: float = 0.05
    # Tenor used to recompute implicit yields from cut-off prices.
    rf_tenor_days: int = 91
    rf_day_count_basis: int = 365
    # Auctions retained before the study start so later phases can do an as-of
    # lookup on the first trading days of the study period.
    rf_lookback_days: int = 31

    # Alignment ------------------------------------------------------------------
    min_common_session_coverage: float = 0.95


DEFAULT_THRESHOLDS = QualityThresholds()
