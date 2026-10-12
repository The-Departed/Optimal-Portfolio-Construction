"""Correlation and covariance on a common sample, with numerical validation.

Matrices are estimated only from complete (gap-free) return tables so that every
pairwise entry uses the same dates; pairwise-deletion windows are never mixed.
Validation reports problems; it never modifies a matrix.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analytics.conventions import DEFAULT_CONVENTIONS, Conventions


@dataclass(frozen=True, slots=True)
class MatrixDiagnostics:
    labels: tuple[str, ...]
    observations: int
    symmetric: bool
    max_asymmetry: float
    finite: bool
    min_eigenvalue: float
    max_eigenvalue: float
    positive_semidefinite: bool
    condition_number: float | None
    diagonal_ok: bool
    within_bounds: bool

    @property
    def valid(self) -> bool:
        return (
            self.symmetric
            and self.finite
            and self.positive_semidefinite
            and self.diagonal_ok
            and self.within_bounds
        )

    def problems(self) -> list[str]:
        out = []
        if not self.finite:
            out.append("matrix contains non-finite values")
        if not self.symmetric:
            out.append(f"matrix is not symmetric (max asymmetry {self.max_asymmetry:.3e})")
        if not self.positive_semidefinite:
            out.append(
                f"matrix is not positive semidefinite (min eigenvalue {self.min_eigenvalue:.3e})"
            )
        if not self.diagonal_ok:
            out.append("diagonal entries are invalid")
        if not self.within_bounds:
            out.append("entries outside the valid range")
        return out


def require_common_sample(returns: pd.DataFrame) -> None:
    if returns.isna().any().any():
        missing = returns.isna().sum()
        raise ValueError(
            "returns contain missing values "
            f"({ {k: int(v) for k, v in missing[missing > 0].items()} }); "
            "matrices must be estimated on one common sample"
        )
    if len(returns) < 2:
        raise ValueError("at least two return observations are required")


def pairwise_observations(returns: pd.DataFrame) -> pd.DataFrame:
    """Number of dates on which both series have a value (documents sample alignment)."""
    mask = returns.notna().astype(int)
    counts = mask.T @ mask
    return counts.astype(int)


def covariance_matrix(
    returns: pd.DataFrame, conventions: Conventions = DEFAULT_CONVENTIONS
) -> pd.DataFrame:
    require_common_sample(returns)
    return returns.cov(ddof=conventions.ddof)


def annualize_covariance(
    daily: pd.DataFrame, conventions: Conventions = DEFAULT_CONVENTIONS
) -> pd.DataFrame:
    return daily * conventions.periods_per_year


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    require_common_sample(returns)
    constant = returns.columns[returns.std(ddof=1) == 0]
    if len(constant):
        raise ValueError(f"correlation undefined for constant series: {list(constant)}")
    return returns.corr(method="pearson")


def diagnose(
    matrix: pd.DataFrame,
    observations: int,
    *,
    kind: str,
    conventions: Conventions = DEFAULT_CONVENTIONS,
) -> MatrixDiagnostics:
    """Validate a covariance (``kind="covariance"``) or correlation matrix."""
    if list(matrix.index) != list(matrix.columns):
        raise ValueError("row and column labels differ")
    m = matrix.to_numpy(dtype="float64")
    finite = bool(np.isfinite(m).all())
    asym = float(np.abs(m - m.T).max()) if finite else float("inf")
    scale = max(float(np.abs(m).max()), 1e-300) if finite else 1.0
    symmetric = finite and asym <= conventions.symmetry_tolerance * scale
    if finite:
        eig = np.linalg.eigvalsh((m + m.T) / 2)
        lo, hi = float(eig.min()), float(eig.max())
        psd = lo >= -conventions.psd_relative_tolerance * max(abs(hi), 1e-300)
        cond = float(hi / lo) if lo > 0 else None
    else:
        lo = hi = float("nan")
        psd, cond = False, None
    diag = np.diag(m)
    tol = conventions.correlation_bound_tolerance
    if kind == "correlation":
        diagonal_ok = finite and bool(np.allclose(diag, 1.0, atol=tol))
        within = finite and bool((np.abs(m) <= 1.0 + tol).all())
    elif kind == "covariance":
        diagonal_ok = finite and bool((diag > 0).all())
        within = True
    else:
        raise ValueError(f"unknown matrix kind {kind!r}")
    return MatrixDiagnostics(
        labels=tuple(str(x) for x in matrix.index),
        observations=observations,
        symmetric=symmetric,
        max_asymmetry=asym,
        finite=finite,
        min_eigenvalue=lo,
        max_eigenvalue=hi,
        positive_semidefinite=psd,
        condition_number=cond,
        diagonal_ok=diagonal_ok,
        within_bounds=within,
    )
