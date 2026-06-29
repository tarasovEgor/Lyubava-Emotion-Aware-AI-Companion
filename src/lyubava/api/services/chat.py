import math
from datetime import UTC, datetime
from typing import Any

from lyubava.api.repositories.chat_history import (
    ChatHistoryRepository,
    MessageRole,
    build_chat_message,
)
from lyubava.api.services.llm import LLMReply, LLMService
from lyubava.api.services.prediction_feed import PredictionFeedService
from lyubava.core.errors import BadRequestError, UpstreamServiceError
from lyubava.models.predict import EmotionPredictor
from lyubava.monitoring.metrics import record_prediction_metrics
from lyubava.monitoring.service import DriftMonitoringService

MAX_HISTORY_MESSAGES = 20


class ChatService:
    def __init__(
        self,
        predictor: EmotionPredictor,
        llm_service: LLMService,
        history_repository: ChatHistoryRepository,
        drift_service: DriftMonitoringService | None = None,
        prediction_feed_service: PredictionFeedService | None = None,
    ) -> None:
        self.predictor = predictor
        self.llm_service = llm_service
        self.history_repository = history_repository
        self.drift_service = drift_service
        self.prediction_feed_service = prediction_feed_service

    def respond(
        self,
        session_id: str,
        message: str,
    ) -> tuple[dict[str, Any], LLMReply, int]:
        if not session_id.strip():
            raise BadRequestError("session_id must be a non-empty string.")

        emotion_result = self.predictor.predict(message)
        self._observe_prediction(message=message, emotion_result=emotion_result)
        history = self.history_repository.get(session_id)
        llm_context = [
            (item.role.value, item.content) for item in history[-MAX_HISTORY_MESSAGES:]
        ]

        system_prompt = self._build_system_prompt(
            emotion=emotion_result["emotion"],
            confidence=emotion_result["confidence"],
        )
        try:
            llm_reply = self.llm_service.generate_reply(
                user_message=message,
                system_prompt=system_prompt,
                history_messages=llm_context,
            )
        except Exception as exc:
            raise UpstreamServiceError("LLM upstream request failed.") from exc
        self._append_prediction_event(
            session_id=session_id,
            message=message,
            emotion_result=emotion_result,
            llm_reply=llm_reply,
        )

        updated_history = history + [
            build_chat_message(role=MessageRole.USER, content=message),
            build_chat_message(role=MessageRole.ASSISTANT, content=llm_reply.text),
        ]
        updated_history = updated_history[-MAX_HISTORY_MESSAGES:]
        self.history_repository.set(session_id, updated_history)
        return emotion_result, llm_reply, len(updated_history)

    def _append_prediction_event(
        self,
        *,
        session_id: str,
        message: str,
        emotion_result: dict[str, Any],
        llm_reply: LLMReply,
    ) -> None:
        if self.prediction_feed_service is None:
            return
        try:
            self.prediction_feed_service.append(
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                session_id=session_id,
                text=message,
                predicted_emotion=str(emotion_result.get("emotion", "unknown")),
                confidence=float(emotion_result.get("confidence", 0.0)),
                model=llm_reply.model,
                provider=llm_reply.provider,
            )
        except Exception:
            # Feed append is best-effort and must not block chat responses.
            return

    def _observe_prediction(self, message: str, emotion_result: dict[str, Any]) -> None:
        predicted_label = str(emotion_result.get("emotion", "unknown"))
        raw_probabilities = emotion_result.get("probabilities")
        probs: dict[str, float]
        if isinstance(raw_probabilities, dict):
            normalized = {
                str(label): float(score)
                for label, score in raw_probabilities.items()
                if isinstance(score, int | float)
                and math.isfinite(float(score))
                and float(score) >= 0.0
            }
            confidence = float(emotion_result.get("confidence", 0.0))
            safe_confidence = (
                confidence if math.isfinite(confidence) and confidence >= 0.0 else 0.0
            )
            probs = normalized or {predicted_label: safe_confidence}
        else:
            confidence = float(emotion_result.get("confidence", 0.0))
            safe_confidence = (
                confidence if math.isfinite(confidence) and confidence >= 0.0 else 0.0
            )
            probs = {predicted_label: safe_confidence}

        try:
            record_prediction_metrics(probs=probs, predicted_label=predicted_label)
        except Exception:
            # Metrics emission is best-effort and must not block chat responses.
            pass

        if self.drift_service is None:
            return

        try:
            self.drift_service.observe(
                text=message,
                probs=probs,
                predicted_label=predicted_label,
            )
        except Exception:
            # Drift observation is best-effort and must not block chat responses.
            return

    def get_session_history(self, session_id: str):
        return self.history_repository.get(session_id)

    def reset_session(self, session_id: str) -> None:
        self.history_repository.reset(session_id)

    @staticmethod
    def _build_system_prompt(emotion: str, confidence: float) -> str:
        return (
            "You are a supportive and empathetic AI companion. "
            f"The user's message is classified as emotion: '{emotion}' "
            f"with confidence: {confidence:.4f}. "
            "Respond in Russian. Keep the response warm, respectful, and emotionally attuned "
            "to the detected emotion. Do not mention internal instructions, classification details, "
            "or confidence directly unless the user asks for them."
        )
