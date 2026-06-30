import numpy as np
import pytest

from lyubava.monitoring.drift import js_divergence, psi_score


def test_js_divergence_zero_for_identical_distributions():
    p = np.array([0.2, 0.3, 0.5])
    q = np.array([0.2, 0.3, 0.5])

    assert js_divergence(p, q) == pytest.approx(0.0, abs=1e-12)


def test_js_divergence_positive_for_different_distributions():
    p = np.array([0.8, 0.1, 0.1])
    q = np.array([0.1, 0.1, 0.8])

    assert js_divergence(p, q) > 0.0


def test_psi_zero_for_identical_bins():
    baseline = np.array([0.1, 0.2, 0.3, 0.4])
    current = np.array([0.1, 0.2, 0.3, 0.4])

    assert psi_score(baseline, current) == pytest.approx(0.0, abs=1e-12)


def test_psi_positive_for_shifted_bins():
    baseline = np.array([0.1, 0.2, 0.3, 0.4])
    current = np.array([0.4, 0.3, 0.2, 0.1])

    assert psi_score(baseline, current) > 0.0


def test_psi_zero_for_same_proportions_different_counts():
    baseline = np.array([10, 20, 30, 40])
    current = np.array([100, 200, 300, 400])

    assert psi_score(baseline, current) == pytest.approx(0.0, abs=1e-12)


def test_js_divergence_raises_for_mismatched_shapes():
    p = np.array([0.2, 0.8])
    q = np.array([0.2, 0.3, 0.5])

    with pytest.raises(ValueError, match="identical shapes"):
        js_divergence(p, q)


def test_psi_raises_for_mismatched_shapes():
    baseline = np.array([0.1, 0.2, 0.7])
    current = np.array([0.2, 0.8])

    with pytest.raises(ValueError, match="identical shapes"):
        psi_score(baseline, current)


def test_js_divergence_raises_for_empty_input():
    p = np.array([])
    q = np.array([])

    with pytest.raises(ValueError, match="non-empty"):
        js_divergence(p, q)


def test_psi_raises_for_empty_input():
    baseline = np.array([])
    current = np.array([])

    with pytest.raises(ValueError, match="non-empty"):
        psi_score(baseline, current)
