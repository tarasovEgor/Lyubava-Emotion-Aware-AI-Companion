import pytest

from lyubava.api.repositories.chat_history import InMemoryChatHistoryRepository
from lyubava.api.services.chat import ChatService
from lyubava.api.services.llm import LLMReply
from lyubava.core.errors import BadRequestError, UpstreamServiceError


class FakePredictor:
    def predict(self, text: str) -> dict[str, str | float]:
        return {"emotion": "joy", "confidence": 0.87}


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
