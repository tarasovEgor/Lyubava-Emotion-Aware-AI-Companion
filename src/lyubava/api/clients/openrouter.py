from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from lyubava.api.services.llm import LLMReply
from lyubava.core.config import Settings


class OpenRouterLLMClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")

        self.model = settings.openrouter_model
        self.client = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            temperature=settings.chat_temperature,
        )

    def generate_reply(
        self,
        user_message: str,
        system_prompt: str,
        history_messages: list[tuple[str, str]] | None = None,
    ) -> LLMReply:
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=system_prompt)
        ]
        for role, content in history_messages or []:
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        messages.append(HumanMessage(content=user_message))

        response = self.client.invoke(messages)
        return LLMReply(
            text=self._extract_text(response.content),
            model=self.model,
            provider="openrouter",
            system_prompt=system_prompt,
            usage=self._normalize_usage(getattr(response, "usage_metadata", None)),
            response_metadata=self._normalize_response_metadata(
                getattr(response, "response_metadata", None)
            ),
        )

    @staticmethod
    def _extract_text(content: str | list[Any]) -> str:
        if isinstance(content, str):
            return content.strip()

        parts: list[str] = []
        for chunk in content:
            if isinstance(chunk, str):
                parts.append(chunk)
                continue
            if isinstance(chunk, dict):
                text = chunk.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part.strip() for part in parts if part.strip())

    @staticmethod
    def _normalize_usage(usage: Any) -> dict[str, int] | None:
        if not isinstance(usage, dict):
            return None
        normalized = {
            key: value for key, value in usage.items() if isinstance(value, int)
        }
        return normalized or None

    @staticmethod
    def _normalize_response_metadata(
        metadata: Any,
    ) -> dict[str, str | int | float | bool | None] | None:
        if not isinstance(metadata, dict):
            return None
        normalized: dict[str, str | int | float | bool | None] = {}
        for key, value in metadata.items():
            if isinstance(value, str | int | float | bool) or value is None:
                normalized[key] = value
        return normalized or None
