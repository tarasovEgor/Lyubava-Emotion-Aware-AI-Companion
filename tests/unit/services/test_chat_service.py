import pytest

import lyubava.api.services.chat as chat_module
import lyubava.monitoring.metrics as metrics_module
from lyubava.api.repositories.chat_history import InMemoryChatHistoryRepository
from lyubava.api.services.chat import ChatService
from lyubava.api.services.llm import LLMReply
from lyubava.core.errors import BadRequestError, UpstreamServiceError


class FakePredictor:
    def predict(self, text: str) -> dict[str, str | float]:
        return {"emotion": "joy", "confidence": 0.87}


class FakePredictorWithProbabilities:
    def predict(self, text: str) -> dict[str, str | float | dict[str, float]]:
        return {
            "emotion": "joy",
            "confidence": 0.87,
            "probabilities": {"joy": 0.87, "sadness": 0.13},
        }


class FakePredictorWithInvalidProbabilities:
    def predict(self, text: str) -> dict[str, str | float | dict[str, float]]:
        return {
            "emotion": "joy",
            "confidence": 0.87,
            "probabilities": {
                "joy": 0.87,
                "sadness": float("nan"),
                "anger": float("inf"),
                "fear": -0.2,
            },
        }


class FakePredictorWithOnlyInvalidProbabilities:
    def predict(self, text: str) -> dict[str, str | float | dict[str, float]]:
        return {
            "emotion": "joy",
            "confidence": float("nan"),
            "probabilities": {
                "joy": float("nan"),
                "sadness": float("inf"),
                "fear": -1.0,
            },
        }


class FakeLLM:
    def generate_reply(
        self,
        user_message: str,
        system_prompt: str,
        history_messages: list[tuple[str, str]] | None = None,
    ) -> LLMReply:
        return LLMReply(
            text=f"reply:{user_message}",
            model="fake-model",
            provider="fake",
            system_prompt=system_prompt,
            usage={"input_tokens": 10, "output_tokens": 4},
            response_metadata={"finish_reason": "stop"},
        )


class FailingLLM:
    def generate_reply(
        self,
        user_message: str,
        system_prompt: str,
        history_messages: list[tuple[str, str]] | None = None,
    ) -> LLMReply:
        raise RuntimeError("upstream timeout")


class RecordingDriftService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, float], str]] = []

    def observe(self, text: str, probs: dict[str, float], predicted_label: str) -> None:
        self.calls.append((text, probs, predicted_label))


class FailingDriftService:
    def observe(self, text: str, probs: dict[str, float], predicted_label: str) -> None:
        raise RuntimeError("drift unavailable")


class RecordingPredictionFeedService:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def append(self, **kwargs: object) -> None:
        self.items.append(kwargs)


class FailingPredictionFeedService:
    def append(self, **kwargs: object) -> None:
        _ = kwargs
        raise RuntimeError("feed unavailable")


def test_chat_service_respond_and_persist_history():
    service = ChatService(
        predictor=FakePredictor(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
    )

    emotion_result, llm_reply, history_length = service.respond("s1", "hi")
    assert emotion_result["emotion"] == "joy"
    assert llm_reply.text == "reply:hi"
    assert history_length == 2
    history = service.get_session_history("s1")
    assert len(history) == 2
    assert history[0].role.value == "user"
    assert history[1].role.value == "assistant"


def test_chat_service_rejects_empty_session_id():
    service = ChatService(
        predictor=FakePredictor(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
    )

    with pytest.raises(BadRequestError):
        service.respond("", "hello")


def test_chat_service_maps_llm_errors_to_upstream():
    service = ChatService(
        predictor=FakePredictor(),
        llm_service=FailingLLM(),
        history_repository=InMemoryChatHistoryRepository(),
    )

    with pytest.raises(UpstreamServiceError):
        service.respond("s1", "hello")


def test_chat_service_observes_full_probability_distribution_when_available():
    drift = RecordingDriftService()
    service = ChatService(
        predictor=FakePredictorWithProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        drift_service=drift,
    )

    service.respond("s1", "hi")

    assert len(drift.calls) == 1
    text, probs, predicted_label = drift.calls[0]
    assert text == "hi"
    assert predicted_label == "joy"
    assert probs == {"joy": 0.87, "sadness": 0.13}


def test_chat_service_observation_falls_back_to_top1_probability():
    drift = RecordingDriftService()
    service = ChatService(
        predictor=FakePredictor(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        drift_service=drift,
    )

    service.respond("s1", "hi")

    assert len(drift.calls) == 1
    text, probs, predicted_label = drift.calls[0]
    assert text == "hi"
    assert predicted_label == "joy"
    assert probs == {"joy": 0.87}


def test_chat_service_ignores_drift_observation_errors():
    service = ChatService(
        predictor=FakePredictorWithProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        drift_service=FailingDriftService(),
    )

    emotion_result, llm_reply, history_length = service.respond("s1", "hi")

    assert emotion_result["emotion"] == "joy"
    assert llm_reply.text == "reply:hi"
    assert history_length == 2


def test_chat_service_records_prediction_metrics(monkeypatch):
    captured: dict[str, object] = {}

    def fake_record_prediction_metrics(
        probs: dict[str, float], predicted_label: str
    ) -> None:
        captured["probs"] = probs
        captured["predicted_label"] = predicted_label

    monkeypatch.setattr(
        chat_module,
        "record_prediction_metrics",
        fake_record_prediction_metrics,
        raising=False,
    )

    service = ChatService(
        predictor=FakePredictorWithProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
    )

    service.respond("s1", "hi")

    assert captured == {
        "probs": {"joy": 0.87, "sadness": 0.13},
        "predicted_label": "joy",
    }


def test_chat_service_ignores_prediction_metric_errors(monkeypatch):
    calls = 0

    def failing_record_prediction_metrics(
        probs: dict[str, float], predicted_label: str
    ) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("metrics down")

    monkeypatch.setattr(
        chat_module,
        "record_prediction_metrics",
        failing_record_prediction_metrics,
        raising=False,
    )

    service = ChatService(
        predictor=FakePredictorWithProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
    )

    emotion_result, llm_reply, history_length = service.respond("s1", "hi")

    assert calls == 1
    assert emotion_result["emotion"] == "joy"
    assert llm_reply.text == "reply:hi"
    assert history_length == 2


def test_chat_service_filters_non_finite_and_negative_probabilities(monkeypatch):
    recorded_metrics: list[dict[str, float]] = []
    drift = RecordingDriftService()

    def fake_record_prediction_metrics(
        probs: dict[str, float], predicted_label: str
    ) -> None:
        _ = predicted_label
        recorded_metrics.append(probs)

    monkeypatch.setattr(
        chat_module,
        "record_prediction_metrics",
        fake_record_prediction_metrics,
    )

    service = ChatService(
        predictor=FakePredictorWithInvalidProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        drift_service=drift,
    )

    service.respond("s1", "hi")

    assert recorded_metrics == [{"joy": 0.87}]
    assert len(drift.calls) == 1
    _, probs, _ = drift.calls[0]
    assert probs == {"joy": 0.87}


def test_chat_service_falls_back_to_zero_when_all_probabilities_invalid(monkeypatch):
    recorded_metrics: list[dict[str, float]] = []
    drift = RecordingDriftService()

    def fake_record_prediction_metrics(
        probs: dict[str, float], predicted_label: str
    ) -> None:
        _ = predicted_label
        recorded_metrics.append(probs)

    monkeypatch.setattr(
        chat_module,
        "record_prediction_metrics",
        fake_record_prediction_metrics,
    )

    service = ChatService(
        predictor=FakePredictorWithOnlyInvalidProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        drift_service=drift,
    )

    service.respond("s1", "hi")

    assert recorded_metrics == [{"joy": 0.0}]
    assert len(drift.calls) == 1
    _, probs, _ = drift.calls[0]
    assert probs == {"joy": 0.0}


def test_record_prediction_metrics_sanitizes_invalid_inputs(monkeypatch):
    class RecordingGauge:
        def __init__(self) -> None:
            self.values: list[float] = []

        def set(self, value: float) -> None:
            self.values.append(value)

        def labels(self, **kwargs):
            _ = kwargs
            return self

    class RecordingCounter:
        def __init__(self) -> None:
            self.count = 0

        def inc(self) -> None:
            self.count += 1

    confidence_gauge = RecordingGauge()
    entropy_gauge = RecordingGauge()
    class_ratio_gauge = RecordingGauge()
    predictions_counter = RecordingCounter()

    monkeypatch.setattr(metrics_module, "_prediction_observation_count", 0)
    monkeypatch.setattr(metrics_module, "_prediction_confidence_sum", 0.0)
    monkeypatch.setattr(metrics_module, "_prediction_entropy_sum", 0.0)
    monkeypatch.setattr(metrics_module, "_prediction_label_counts", {})
    monkeypatch.setattr(metrics_module, "_prediction_confidence_mean", confidence_gauge)
    monkeypatch.setattr(metrics_module, "_prediction_entropy_mean", entropy_gauge)
    monkeypatch.setattr(metrics_module, "_prediction_class_ratio", class_ratio_gauge)
    monkeypatch.setattr(metrics_module, "_predictions_total", predictions_counter)

    metrics_module.record_prediction_metrics(
        probs={"joy": float("nan"), "sadness": float("inf"), "fear": -0.5},
        predicted_label="joy",
    )

    assert predictions_counter.count == 1
    assert confidence_gauge.values[-1] == 0.0
    assert entropy_gauge.values[-1] == 0.0
    assert class_ratio_gauge.values[-1] == 1.0


def test_chat_service_appends_prediction_feed_event():
    feed = RecordingPredictionFeedService()
    service = ChatService(
        predictor=FakePredictorWithProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        prediction_feed_service=feed,
    )

    service.respond("session-42", "hello there")

    assert len(feed.items) == 1
    item = feed.items[0]
    assert item["session_id"] == "session-42"
    assert item["text"] == "hello there"
    assert item["predicted_emotion"] == "joy"
    assert item["confidence"] == 0.87
    assert item["model"] == "fake-model"
    assert item["provider"] == "fake"
    assert isinstance(item["timestamp"], str)
    assert str(item["timestamp"]).endswith("Z")


def test_chat_service_ignores_prediction_feed_errors():
    service = ChatService(
        predictor=FakePredictorWithProbabilities(),
        llm_service=FakeLLM(),
        history_repository=InMemoryChatHistoryRepository(),
        prediction_feed_service=FailingPredictionFeedService(),
    )

    emotion_result, llm_reply, history_length = service.respond("s1", "hi")

    assert emotion_result["emotion"] == "joy"
    assert llm_reply.text == "reply:hi"
    assert history_length == 2
