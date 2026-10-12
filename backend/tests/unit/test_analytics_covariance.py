import numpy as np
import pandas as pd
import pytest

from app.analytics.covariance import (
    annualize_covariance,
    correlation_matrix,
    covariance_matrix,
    diagnose,
    pairwise_observations,
)

IDX = pd.bdate_range("2024-01-01", periods=6)


def _returns() -> pd.DataFrame:
    a = np.array([0.01, -0.02, 0.015, 0.0, 0.005, -0.01])
    return pd.DataFrame(
        {"A": a, "B": 2 * a, "C": -a, "D": [0.003, 0.001, -0.002, 0.004, -0.001, 0.0]}, index=IDX
    )


def test_correlation_known_values_order_and_shape() -> None:
    corr = correlation_matrix(_returns())
    assert list(corr.index) == list(corr.columns) == ["A", "B", "C", "D"]
    assert corr.loc["A", "B"] == pytest.approx(1.0)
    assert corr.loc["A", "C"] == pytest.approx(-1.0)
    d = diagnose(corr, 6, kind="correlation")
    assert d.symmetric and d.diagonal_ok and d.within_bounds and d.positive_semidefinite and d.valid


def test_covariance_sample_estimator_and_annualization() -> None:
    r = _returns()
    daily = covariance_matrix(r)
    a = r["A"].to_numpy()
    assert daily.loc["A", "A"] == pytest.approx(a.var(ddof=1))
    assert daily.loc["A", "B"] == pytest.approx(2 * a.var(ddof=1))
    annual = annualize_covariance(daily)
    np.testing.assert_allclose(annual.to_numpy(), daily.to_numpy() * 252)
    assert diagnose(annual, 6, kind="covariance").valid


def test_missing_values_are_rejected_not_pairwise_mixed() -> None:
    r = _returns()
    r.iloc[2, 1] = np.nan
    counts = pairwise_observations(r)
    assert counts.loc["A", "A"] == 6 and counts.loc["A", "B"] == 5  # documents the mismatch
    with pytest.raises(ValueError, match="common sample"):
        covariance_matrix(r)
    with pytest.raises(ValueError, match="common sample"):
        correlation_matrix(r)


def test_constant_series_correlation_is_undefined() -> None:
    r = _returns()
    r["D"] = 0.001
    with pytest.raises(ValueError, match="constant"):
        correlation_matrix(r)


def test_non_psd_matrix_is_reported_not_repaired() -> None:
    labels = ["A", "B", "C"]
    bad = pd.DataFrame(
        [[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]], index=labels, columns=labels, dtype=float
    )
    original = bad.copy()
    d = diagnose(bad, 100, kind="correlation")
    assert not d.positive_semidefinite and d.min_eigenvalue < 0
    assert any("positive semidefinite" in p for p in d.problems())
    pd.testing.assert_frame_equal(bad, original)


def test_asymmetry_bounds_and_label_checks() -> None:
    labels = ["A", "B"]
    asym = pd.DataFrame([[1.0, 0.5], [0.4, 1.0]], index=labels, columns=labels)
    assert not diagnose(asym, 10, kind="correlation").symmetric
    out_of_range = pd.DataFrame([[1.0, 1.2], [1.2, 1.0]], index=labels, columns=labels)
    assert not diagnose(out_of_range, 10, kind="correlation").within_bounds
    with pytest.raises(ValueError, match="labels"):
        diagnose(
            pd.DataFrame([[1.0, 0.0], [0.0, 1.0]], index=labels, columns=["B", "A"]),
            10,
            kind="correlation",
        )
