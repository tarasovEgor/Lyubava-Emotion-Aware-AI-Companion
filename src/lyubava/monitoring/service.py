from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

from lyubava.monitoring.drift import js_divergence, psi_score
from lyubava.monitoring.metrics import update_drift_snapshot

LOW_CONFIDENCE_THRESHOLD = 0.5
_CONCEPT_COMPONENT_WEIGHT = 1.0 / 3.0


@dataclass(frozen=True)
class DriftThresholds:
    data_warn: float
    data_critical: float
    concept_warn: float
    concept_critical: float
    target_warn: float
    target_critical: float


class DriftMonitoringService:
    def __init__(
        self,
        thresholds: DriftThresholds,
        window_size: int,
        min_samples: int,
        baseline_stats: dict[str, Any] | None = None,
    ) -> None:
        parsed_window_size = int(window_size)
        parsed_min_samples = int(min_samples)
        if parsed_window_size < 1:
            raise ValueError("window_size must be greater than or equal to 1")
        if parsed_min_samples < 1:
            raise ValueError("min_samples must be greater than or equal to 1")
        if parsed_min_samples > parsed_window_size:
            raise ValueError("min_samples must be less than or equal to window_size")

        self._thresholds = thresholds
        self._window_size = parsed_window_size
        self._min_samples = parsed_min_samples
        self._baseline_stats = baseline_stats or {}
        self._texts: deque[str] = deque(maxlen=self._window_size)
        self._probabilities: deque[dict[str, float]] = deque(maxlen=self._window_size)
        self._predicted_labels: deque[str] = deque(maxlen=self._window_size)
        self._last_update: datetime | None = None

    def observe(self, text: str, probs: dict[str, float], predicted_label: str) -> None:
        self._texts.append(text)
        self._probabilities.append(probs)
        self._predicted_labels.append(predicted_label)
        self._last_update = datetime.now(UTC)

    def snapshot(self) -> dict[str, Any]:
        sample_count = len(self._texts)
        drift = {
            "data": self._insufficient_section(),
            "concept": self._insufficient_section(),
            "target": self._insufficient_section(),
        }
        service_status = "insufficient_data"

        if sample_count >= self._min_samples:
            data_score = self._compute_data_drift()
            concept_score = self._compute_concept_drift()
            target_score = self._compute_target_drift()
            drift = {
                "data": self._build_section(
                    score=data_score,
                    warn=self._thresholds.data_warn,
                    critical=self._thresholds.data_critical,
                ),
                "concept": self._build_section(
                    score=concept_score,
                    warn=self._thresholds.concept_warn,
                    critical=self._thresholds.concept_critical,
                ),
                "target": self._build_section(
                    score=target_score,
                    warn=self._thresholds.target_warn,
                    critical=self._thresholds.target_critical,
                ),
            }

            if any(section["status"] == "unavailable" for section in drift.values()):
                service_status = "unavailable"
            else:
                service_status = "ok"

        snapshot = {
            "service_status": service_status,
            "window_size": self._window_size,
            "min_samples": self._min_samples,
            "sample_count": sample_count,
            "drift": drift,
            "last_update": self._format_timestamp(self._last_update),
        }
        try:
            update_drift_snapshot(snapshot)
        except Exception:
            # Metrics emission is best-effort and must not block monitoring API consumers.
            pass
        return snapshot

    def _compute_data_drift(self) -> float | None:
        baseline_bins = self._baseline_stats.get("text_length_bins") or self._baseline_stats.get(
            "data_bins"
        )
        if baseline_bins is None:
            return None

        baseline = np.asarray(baseline_bins, dtype=float)
        if baseline.size == 0:
            return None

        current = np.asarray(self._current_text_bins(), dtype=float)
        if baseline.shape != current.shape:
            return None
        return psi_score(baseline, current)

    def _compute_concept_drift(self) -> float | None:
        baseline_proxy = self._baseline_stats.get("concept_proxy")
        if not baseline_proxy:
            return None

        required_keys = {"mean_confidence", "mean_entropy", "low_confidence_ratio"}
        if not required_keys.issubset(baseline_proxy.keys()):
            return None

        baseline_confidence = float(baseline_proxy["mean_confidence"])
        baseline_entropy = float(baseline_proxy["mean_entropy"])
        baseline_low_conf_ratio = float(baseline_proxy["low_confidence_ratio"])

        current_confidence = self._mean_prediction_confidence()
        current_entropy = self._mean_prediction_entropy()
        current_low_conf_ratio = self._low_confidence_ratio()

        # MVP concept proxy: average absolute shifts across three simple confidence/uncertainty components.
        return float(
            _CONCEPT_COMPONENT_WEIGHT * abs(current_confidence - baseline_confidence)
            + _CONCEPT_COMPONENT_WEIGHT * abs(current_entropy - baseline_entropy)
            + _CONCEPT_COMPONENT_WEIGHT * abs(current_low_conf_ratio - baseline_low_conf_ratio)
        )

    def _compute_target_drift(self) -> float | None:
        baseline_dist = self._baseline_stats.get("class_distribution")
        if not baseline_dist:
            return None

        classes = sorted(set(baseline_dist.keys()) | set(self._predicted_labels))
        baseline = np.asarray([float(baseline_dist.get(name, 0.0)) for name in classes], dtype=float)
        current = np.asarray(self._predicted_label_distribution(classes), dtype=float)
        return js_divergence(baseline, current)

    def _current_text_bins(self) -> list[int]:
        bins = [0, 0, 0]
        for text in self._texts:
            length = len(text)
            if length < 32:
                bins[0] += 1
            elif length < 96:
                bins[1] += 1
            else:
                bins[2] += 1
        return bins

    def _mean_prediction_confidence(self) -> float:
        if not self._probabilities:
            return 0.0
        return float(np.mean([max(probs.values(), default=0.0) for probs in self._probabilities]))

    def _mean_prediction_entropy(self) -> float:
        if not self._probabilities:
            return 0.0

        entropies: list[float] = []
        for probs in self._probabilities:
            values = np.asarray(list(probs.values()), dtype=float)
            if values.size == 0:
                entropies.append(0.0)
                continue
            clipped = np.clip(values, 1e-9, 1.0)
            normalized = clipped / clipped.sum()
            entropies.append(float(-np.sum(normalized * np.log(normalized))))
        return float(np.mean(entropies))

    def _low_confidence_ratio(self) -> float:
        if not self._probabilities:
            return 0.0
        low_count = sum(
            1 for probs in self._probabilities if max(probs.values(), default=0.0) < LOW_CONFIDENCE_THRESHOLD
        )
        return float(low_count / len(self._probabilities))

    def _predicted_label_distribution(self, classes: list[str]) -> list[float]:
        if not self._predicted_labels:
            return [0.0 for _ in classes]

        counts = {name: 0 for name in classes}
        for label in self._predicted_labels:
            counts[label] = counts.get(label, 0) + 1
        total = float(len(self._predicted_labels))
        return [counts.get(name, 0) / total for name in classes]

    @staticmethod
    def _build_section(score: float | None, warn: float, critical: float) -> dict[str, Any]:
        if score is None:
            return {"score": None, "status": "unavailable"}
        if not math.isfinite(score):
            return {"score": None, "status": "unavailable"}
        if score >= critical:
            return {"score": score, "status": "critical"}
        if score >= warn:
            return {"score": score, "status": "warn"}
        return {"score": score, "status": "ok"}

    @staticmethod
    def _insufficient_section() -> dict[str, Any]:
        return {"score": None, "status": "insufficient_data"}

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat().replace("+00:00", "Z")
