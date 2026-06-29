from __future__ import annotations

import math
from threading import Lock
from typing import Any

import numpy as np
from prometheus_client import Counter, Gauge

_predictions_total = Counter(
    "lyubava_predictions_total",
    "Total number of observed prediction events.",
)
_prediction_confidence_mean = Gauge(
    "lyubava_prediction_confidence_mean",
    "Running mean of top-1 prediction confidence.",
)
_prediction_entropy_mean = Gauge(
    "lyubava_prediction_entropy_mean",
    "Running mean of prediction entropy.",
)
_prediction_class_ratio = Gauge(
    "lyubava_prediction_class_ratio",
    "Running ratio of predicted labels by class.",
    labelnames=("class",),
)
_drift_data_score = Gauge(
    "lyubava_drift_data_score",
    "Latest data drift score.",
)
_drift_concept_score = Gauge(
    "lyubava_drift_concept_score",
    "Latest concept drift score.",
)
_drift_target_score = Gauge(
    "lyubava_drift_target_score",
    "Latest target drift score.",
)
_drift_status = Gauge(
    "lyubava_drift_status",
    "Current drift status encoded as one-hot labels (1 active, 0 inactive).",
    labelnames=("type", "level"),
)

_KNOWN_DRIFT_TYPES = ("data", "concept", "target")
_KNOWN_DRIFT_LEVELS = ("ok", "warn", "critical", "unavailable", "insufficient_data")

_state_lock = Lock()
_prediction_observation_count = 0
_prediction_confidence_sum = 0.0
_prediction_entropy_sum = 0.0
_prediction_label_counts: dict[str, int] = {}


def _sanitize_probabilities(
    probs: dict[str, float],
    predicted_label: str,
) -> dict[str, float]:
    sanitized = {
        str(label): float(score)
        for label, score in probs.items()
        if isinstance(score, int | float)
        and math.isfinite(float(score))
        and float(score) >= 0.0
    }
    if sanitized:
        return sanitized
    label = predicted_label or "unknown"
    return {label: 0.0}


def _safe_entropy(probabilities: dict[str, float]) -> float:
    if not probabilities:
        return 0.0

    values = np.asarray(list(probabilities.values()), dtype=float)
    if values.size == 0:
        return 0.0

    clipped = np.clip(values, 1e-9, 1.0)
    total = clipped.sum()
    if total <= 0:
        return 0.0
    normalized = clipped / total
    entropy = float(-np.sum(normalized * np.log(normalized)))
    if not math.isfinite(entropy):
        return 0.0
    return entropy


def _safe_score(value: Any) -> float:
    if isinstance(value, int | float):
        score = float(value)
        if math.isfinite(score):
            return score
    return float("nan")


def record_prediction_metrics(probs: dict[str, float], predicted_label: str) -> None:
    global _prediction_observation_count
    global _prediction_confidence_sum
    global _prediction_entropy_sum

    sanitized_probs = _sanitize_probabilities(probs, predicted_label)
    top1_confidence = max(sanitized_probs.values(), default=0.0)
    entropy = _safe_entropy(sanitized_probs)
    if not math.isfinite(top1_confidence):
        top1_confidence = 0.0
    if not math.isfinite(entropy):
        entropy = 0.0
    label = predicted_label or "unknown"

    with _state_lock:
        _prediction_observation_count += 1
        _prediction_confidence_sum += top1_confidence
        _prediction_entropy_sum += entropy
        _prediction_label_counts[label] = _prediction_label_counts.get(label, 0) + 1
        total = float(_prediction_observation_count)

        _prediction_confidence_mean.set(_prediction_confidence_sum / total)
        _prediction_entropy_mean.set(_prediction_entropy_sum / total)
        for class_name, count in _prediction_label_counts.items():
            _prediction_class_ratio.labels(**{"class": class_name}).set(count / total)

    _predictions_total.inc()


def update_drift_snapshot(snapshot: dict[str, Any]) -> None:
    drift = snapshot.get("drift", {})
    data = drift.get("data", {})
    concept = drift.get("concept", {})
    target = drift.get("target", {})

    _drift_data_score.set(_safe_score(data.get("score")))
    _drift_concept_score.set(_safe_score(concept.get("score")))
    _drift_target_score.set(_safe_score(target.get("score")))

    statuses = {
        "data": str(data.get("status", "")),
        "concept": str(concept.get("status", "")),
        "target": str(target.get("status", "")),
    }
    for drift_type in _KNOWN_DRIFT_TYPES:
        current = statuses.get(drift_type, "")
        for level in _KNOWN_DRIFT_LEVELS:
            value = 1.0 if current == level else 0.0
            _drift_status.labels(type=drift_type, level=level).set(value)
