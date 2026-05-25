from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from lyubava.api.clients.openrouter import OpenRouterLLMClient
from lyubava.api.repositories.chat_history import InMemoryChatHistoryRepository
from lyubava.api.services.chat import ChatService
from lyubava.core.config import Settings
from lyubava.models.predict import EmotionPredictor


@dataclass
class AppContainer:
    settings: Settings
    predictor: EmotionPredictor
    chat_service: ChatService | None
    chat_init_error: str | None = None


def build_container(settings: Settings) -> AppContainer:
    predictor = EmotionPredictor(settings.model_dir)
    history_repository = InMemoryChatHistoryRepository()
    chat_init_error: str | None = None
    chat_service: ChatService | None = None
    try:
        llm_client = OpenRouterLLMClient(settings)
        chat_service = ChatService(
            predictor=predictor,
            llm_service=llm_client,
            history_repository=history_repository,
        )
    except RuntimeError as exc:
        chat_init_error = str(exc)

    return AppContainer(
        settings=settings,
        predictor=predictor,
        chat_service=chat_service,
        chat_init_error=chat_init_error,
    )


def create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = build_container(settings)
        yield
        app.state.container = None

    return lifespan
