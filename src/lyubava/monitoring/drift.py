import numpy as np


def _normalize_dist(values: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    clipped = np.clip(values.astype(float), eps, None)
    return clipped / clipped.sum()


def _validate_same_shape(a: np.ndarray, b: np.ndarray, metric: str) -> None:
    if a.shape != b.shape:
        raise ValueError(
            f"{metric} expects arrays with identical shapes, got {a.shape} and {b.shape}"
        )


def _validate_non_empty(values: np.ndarray, metric: str, name: str) -> None:
    if values.size == 0:
        raise ValueError(f"{metric} expects non-empty {name} array")


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    _validate_same_shape(p, q, "js_divergence")
    _validate_non_empty(p, "js_divergence", "p")
    _validate_non_empty(q, "js_divergence", "q")
    p_n = _normalize_dist(p)
    q_n = _normalize_dist(q)

    m = 0.5 * (p_n + q_n)
    kl_pm = np.sum(p_n * np.log(p_n / m))
    kl_qm = np.sum(q_n * np.log(q_n / m))
    return float(0.5 * (kl_pm + kl_qm))


def psi_score(
    baseline_bins: np.ndarray, current_bins: np.ndarray, eps: float = 1e-9
) -> float:
    _validate_same_shape(baseline_bins, current_bins, "psi_score")
    _validate_non_empty(baseline_bins, "psi_score", "baseline_bins")
    _validate_non_empty(current_bins, "psi_score", "current_bins")
    baseline = _normalize_dist(baseline_bins, eps=eps)
    current = _normalize_dist(current_bins, eps=eps)
    return float(np.sum((current - baseline) * np.log(current / baseline)))
