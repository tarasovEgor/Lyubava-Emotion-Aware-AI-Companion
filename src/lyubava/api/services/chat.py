from lyubava.api.repositories.chat_history import (
    ChatHistoryRepository,
    MessageRole,
    build_chat_message,
)
from lyubava.api.services.llm import LLMReply, LLMService
from lyubava.core.errors import BadRequestError, UpstreamServiceError
from lyubava.models.predict import EmotionPredictor

MAX_HISTORY_MESSAGES = 20


class ChatService:
    def __init__(
        self,
        predictor: EmotionPredictor,
        llm_service: LLMService,
        history_repository: ChatHistoryRepository,
    ) -> None:
        self.predictor = predictor
        self.llm_service = llm_service
        self.history_repository = history_repository

    def respond(
        self,
        session_id: str,
        message: str,
    ) -> tuple[dict[str, str | float], LLMReply, int]:
        if not session_id.strip():
            raise BadRequestError("session_id must be a non-empty string.")

        emotion_result = self.predictor.predict(message)
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

        updated_history = history + [
            build_chat_message(role=MessageRole.USER, content=message),
            build_chat_message(role=MessageRole.ASSISTANT, content=llm_reply.text),
        ]
        updated_history = updated_history[-MAX_HISTORY_MESSAGES:]
        self.history_repository.set(session_id, updated_history)
        return emotion_result, llm_reply, len(updated_history)

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
