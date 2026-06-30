from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMReply:
    text: str
    model: str
    provider: str
    system_prompt: str
    usage: dict[str, int] | None
    response_metadata: dict[str, str | int | float | bool | None] | None


class LLMService(Protocol):
    def generate_reply(
        self,
        user_message: str,
        system_prompt: str,
        history_messages: list[tuple[str, str]] | None = None,
    ) -> LLMReply: ...
