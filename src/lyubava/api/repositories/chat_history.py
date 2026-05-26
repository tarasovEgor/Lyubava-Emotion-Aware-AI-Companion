from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol
from uuid import uuid4


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    id: str
    role: MessageRole
    content: str
    created_at: str


class ChatHistoryRepository(Protocol):
    def get(self, session_id: str) -> list[ChatMessage]: ...

    def set(self, session_id: str, messages: list[ChatMessage]) -> None: ...

    def reset(self, session_id: str) -> None: ...


class InMemoryChatHistoryRepository:
    def __init__(self) -> None:
        self._session_history: dict[str, list[ChatMessage]] = {}

    def get(self, session_id: str) -> list[ChatMessage]:
        return self._session_history.get(session_id, [])

    def set(self, session_id: str, messages: list[ChatMessage]) -> None:
        self._session_history[session_id] = messages

    def reset(self, session_id: str) -> None:
        self._session_history.pop(session_id, None)


def build_chat_message(role: MessageRole, content: str) -> ChatMessage:
    return ChatMessage(
        id=str(uuid4()),
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
