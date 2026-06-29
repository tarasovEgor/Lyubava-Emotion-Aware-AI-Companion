from datetime import UTC, datetime

import numpy as np
import pytest

import lyubava.monitoring.service as service_module
from lyubava.monitoring.drift import js_divergence
from lyubava.monitoring.service import DriftMonitoringService, DriftThresholds

BASELINE_CONCEPT_PROXY = {
    "mean_confidence": 0.8,
    "mean_entropy": 0.5,
    "low_confidence_ratio": 0.2,
}


def test_service_returns_insufficient_data_until_min_samples():
    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.1,
            concept_critical=0.2,
            target_warn=0.1,
            target_critical=0.2,
        ),
        window_size=50,
        min_samples=5,
        baseline_stats={"class_distribution": {"joy": 0.5, "sadness": 0.5}},
    )

    for _ in range(3):
        service.observe(
            text="hi",
            probs={"joy": 0.8, "sadness": 0.2},
            predicted_label="joy",
        )

    snapshot = service.snapshot()

    assert snapshot["service_status"] == "insufficient_data"
    assert snapshot["window_size"] == 50
    assert snapshot["min_samples"] == 5
    assert snapshot["sample_count"] == 3
    assert snapshot["drift"]["data"]["status"] == "insufficient_data"
    assert snapshot["drift"]["concept"]["status"] == "insufficient_data"
    assert snapshot["drift"]["target"]["status"] == "insufficient_data"
    assert snapshot["last_update"] is not None


def test_service_maps_drift_statuses_after_min_samples():
    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.01,
            data_critical=0.05,
            concept_warn=0.01,
            concept_critical=0.05,
            target_warn=0.01,
            target_critical=0.05,
        ),
        window_size=10,
        min_samples=3,
        baseline_stats={
            "class_distribution": {"joy": 0.5, "sadness": 0.5},
            "concept_proxy": BASELINE_CONCEPT_PROXY,
        },
    )

    for _ in range(3):
        service.observe(
            text="very long text to skew simple bins",
            probs={"joy": 1.0, "sadness": 0.0},
            predicted_label="joy",
        )

    snapshot = service.snapshot()

    assert snapshot["service_status"] == "unavailable"
    assert snapshot["drift"]["data"]["status"] == "unavailable"
    assert snapshot["drift"]["data"]["score"] is None
    assert snapshot["drift"]["concept"]["status"] in {"warn", "critical"}
    assert snapshot["drift"]["concept"]["score"] is not None
    assert snapshot["drift"]["target"]["status"] in {"warn", "critical"}
    assert snapshot["drift"]["target"]["score"] is not None
    datetime.fromisoformat(snapshot["last_update"].replace("Z", "+00:00")).astimezone(
        UTC
    )


def test_service_keeps_only_last_n_observations():
    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.1,
            concept_critical=0.2,
            target_warn=0.1,
            target_critical=0.2,
        ),
        window_size=3,
        min_samples=1,
        baseline_stats={"class_distribution": {"joy": 0.5, "sadness": 0.5}},
    )

    labels = ["joy", "joy", "sadness", "sadness", "sadness"]
    for label in labels:
        service.observe(
            text=f"txt-{label}",
            probs=(
                {"joy": 0.9, "sadness": 0.1}
                if label == "joy"
                else {"joy": 0.1, "sadness": 0.9}
            ),
            predicted_label=label,
        )

    snapshot = service.snapshot()

    assert snapshot["sample_count"] == 3
    assert snapshot["window_size"] == 3
    assert snapshot["drift"]["target"]["score"] is not None
    assert snapshot["drift"]["target"]["score"] > 0.2


def test_service_uses_js_divergence_for_target_drift():
    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.1,
            concept_critical=0.2,
            target_warn=0.1,
            target_critical=0.5,
        ),
        window_size=5,
        min_samples=5,
        baseline_stats={
            "class_distribution": {"joy": 0.5, "sadness": 0.5},
            "concept_proxy": BASELINE_CONCEPT_PROXY,
        },
    )

    for _ in range(5):
        service.observe(
            text="sample",
            probs={"joy": 0.8, "sadness": 0.2},
            predicted_label="joy",
        )

    snapshot = service.snapshot()
    expected = js_divergence(
        p=np.array([0.5, 0.5]),
        q=np.array([1.0, 0.0]),
    )

    assert snapshot["drift"]["target"]["score"] == pytest.approx(expected)
    assert snapshot["drift"]["target"]["status"] == "warn"


def test_service_raises_when_min_samples_exceeds_window_size():
    with pytest.raises(
        ValueError,
        match="min_samples must be less than or equal to window_size",
    ):
        DriftMonitoringService(
            thresholds=DriftThresholds(
                data_warn=0.1,
                data_critical=0.2,
                concept_warn=0.1,
                concept_critical=0.2,
                target_warn=0.1,
                target_critical=0.2,
            ),
            window_size=4,
            min_samples=5,
            baseline_stats={"class_distribution": {"joy": 0.5, "sadness": 0.5}},
        )


def test_service_computes_concept_proxy_score():
    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.05,
            concept_critical=0.5,
            target_warn=0.9,
            target_critical=0.95,
        ),
        window_size=4,
        min_samples=4,
        baseline_stats={
            "class_distribution": {"joy": 0.5, "sadness": 0.5},
            "concept_proxy": BASELINE_CONCEPT_PROXY,
        },
    )

    observations = [
        {"joy": 0.9, "sadness": 0.1},
        {"joy": 0.8, "sadness": 0.2},
        {"joy": 0.7, "sadness": 0.3},
        {"joy": 0.6, "sadness": 0.4},
    ]
    for probs in observations:
        service.observe(text="sample", probs=probs, predicted_label="joy")

    snapshot = service.snapshot()

    expected_mean_confidence = (0.9 + 0.8 + 0.7 + 0.6) / 4
    expected_entropy = float(
        np.mean(
            [
                -float(
                    np.sum(
                        np.array([p["joy"], p["sadness"]])
                        * np.log(np.array([p["joy"], p["sadness"]]))
                    )
                )
                for p in observations
            ]
        )
    )
    expected_low_conf_ratio = 0.0
    expected_score = (
        abs(expected_mean_confidence - BASELINE_CONCEPT_PROXY["mean_confidence"])
        + abs(expected_entropy - BASELINE_CONCEPT_PROXY["mean_entropy"])
        + abs(expected_low_conf_ratio - BASELINE_CONCEPT_PROXY["low_confidence_ratio"])
    ) / 3.0

    assert snapshot["drift"]["concept"]["score"] == pytest.approx(expected_score)
    assert snapshot["drift"]["concept"]["status"] == "warn"


def test_service_marks_concept_unavailable_without_concept_baseline():
    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.1,
            concept_critical=0.2,
            target_warn=0.1,
            target_critical=0.2,
        ),
        window_size=3,
        min_samples=3,
        baseline_stats={"class_distribution": {"joy": 0.5, "sadness": 0.5}},
    )

    for _ in range(3):
        service.observe(
            text="sample", probs={"joy": 0.8, "sadness": 0.2}, predicted_label="joy"
        )

    snapshot = service.snapshot()

    assert snapshot["drift"]["concept"]["score"] is None
    assert snapshot["drift"]["concept"]["status"] == "unavailable"


def test_service_updates_drift_metrics_on_snapshot(monkeypatch):
    captured: list[dict[str, object]] = []

    def fake_update_drift_snapshot(snapshot: dict[str, object]) -> None:
        captured.append(snapshot)

    monkeypatch.setattr(
        service_module,
        "update_drift_snapshot",
        fake_update_drift_snapshot,
        raising=False,
    )

    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.1,
            concept_critical=0.2,
            target_warn=0.1,
            target_critical=0.2,
        ),
        window_size=3,
        min_samples=1,
        baseline_stats={"class_distribution": {"joy": 0.5, "sadness": 0.5}},
    )
    service.observe(
        text="sample", probs={"joy": 0.9, "sadness": 0.1}, predicted_label="joy"
    )

    snapshot = service.snapshot()

    assert len(captured) == 1
    assert captured[0] == snapshot


def test_service_ignores_drift_metric_update_errors(monkeypatch):
    calls = 0

    def failing_update_drift_snapshot(snapshot: dict[str, object]) -> None:
        _ = snapshot
        nonlocal calls
        calls += 1
        raise RuntimeError("metrics down")

    monkeypatch.setattr(
        service_module,
        "update_drift_snapshot",
        failing_update_drift_snapshot,
        raising=False,
    )

    service = DriftMonitoringService(
        thresholds=DriftThresholds(
            data_warn=0.1,
            data_critical=0.2,
            concept_warn=0.1,
            concept_critical=0.2,
            target_warn=0.1,
            target_critical=0.2,
        ),
        window_size=3,
        min_samples=1,
        baseline_stats={"class_distribution": {"joy": 0.5, "sadness": 0.5}},
    )
    service.observe(
        text="sample", probs={"joy": 0.9, "sadness": 0.1}, predicted_label="joy"
    )

    snapshot = service.snapshot()

    assert calls == 1
    assert snapshot["sample_count"] == 1


@pytest.mark.parametrize("invalid_score", [float("nan"), float("inf"), float("-inf")])
def test_build_section_marks_non_finite_scores_as_unavailable(invalid_score):
    section = DriftMonitoringService._build_section(
        score=invalid_score,
        warn=0.1,
        critical=0.2,
    )

    assert section["score"] is None
    assert section["status"] == "unavailable"
