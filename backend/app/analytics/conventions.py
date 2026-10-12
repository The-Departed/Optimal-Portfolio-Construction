"""Statistical conventions shared by all descriptive analytics.

Every documented choice (docs/methodology.md §3) is a field here, so outputs can record
exactly which conventions produced them.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Conventions:
    # Annualization of daily quantities.
    periods_per_year: int = 252
    # Calendar-time basis for the compound annual growth rate.
    calendar_days_per_year: float = 365.25
    # Sample (unbiased) standard deviation and covariance.
    ddof: int = 1
    # Annualizing over a shorter interval would extrapolate a partial year.
    min_annualization_days: int = 365
    # Minimum observations for each statistic to be reported.
    min_obs_std: int = 2
    min_obs_skew: int = 3
    min_obs_kurtosis: int = 4
    # Numerical tolerances for matrix validation.
    symmetry_tolerance: float = 1e-12
    correlation_bound_tolerance: float = 1e-12
    # Eigenvalues >= -psd_tolerance * max(|eigenvalue|) are treated as non-negative.
    psd_relative_tolerance: float = 1e-10

    def describe(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "return_type": "simple daily returns r_t = P_t / P_(t-1) - 1",
            "mean": "arithmetic mean of daily returns",
            "standard_deviation": f"sample standard deviation (ddof={self.ddof})",
            "skewness": "adjusted Fisher-Pearson standardized moment coefficient G1 "
            "(scipy.stats.skew, bias=False)",
            "kurtosis": "excess kurtosis G2, sample-adjusted (scipy.stats.kurtosis, "
            "fisher=True, bias=False); a normal distribution has 0",
            "cumulative_return": "P_end / P_start - 1 over the sample's first and last prices",
            "annualized_return": "CAGR = (P_end / P_start) ** (calendar_days_per_year / "
            "elapsed_calendar_days) - 1",
            "annualized_mean_return": "arithmetic: mean daily return * periods_per_year "
            "(differs from CAGR; reported separately)",
            "annualized_volatility": "daily sample standard deviation * sqrt(periods_per_year)",
            "covariance": f"sample covariance (ddof={self.ddof}) on the common sample; "
            "annualized = daily * periods_per_year",
            "correlation": "Pearson correlation on the common sample",
        }


DEFAULT_CONVENTIONS = Conventions()
