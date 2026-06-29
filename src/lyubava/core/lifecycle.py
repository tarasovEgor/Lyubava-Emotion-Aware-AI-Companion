import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from lyubava.api.clients.openrouter import OpenRouterLLMClient
from lyubava.api.repositories.chat_history import InMemoryChatHistoryRepository
from lyubava.api.services.chat import ChatService
from lyubava.api.services.prediction_feed import PredictionFeedService
from lyubava.core.config import Settings
from lyubava.models.predict import EmotionPredictor
from lyubava.monitoring.service import DriftMonitoringService, DriftThresholds


@dataclass
class AppContainer:
    settings: Settings
    predictor: EmotionPredictor
    drift_service: DriftMonitoringService | None
    prediction_feed_service: PredictionFeedService
    chat_service: ChatService | None
    drift_init_error: str | None = None
    chat_init_error: str | None = None


def _load_drift_baseline_stats(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    baseline_path = Path(path)
    if not baseline_path.exists():
        raise RuntimeError(f"DRIFT_BASELINE_PATH does not exist: {baseline_path}")

    try:
        content = baseline_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
    except OSError as exc:
        raise RuntimeError(
            f"Failed to read drift baseline file: {baseline_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse drift baseline JSON: {baseline_path}"
        ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Drift baseline JSON must be an object.")
    return parsed


def build_container(settings: Settings) -> AppContainer:
    predictor = EmotionPredictor(settings.model_dir)
    history_repository = InMemoryChatHistoryRepository()
    prediction_feed_service = PredictionFeedService(settings.predictions_feed_max_items)
    drift_init_error: str | None = None
    drift_service: DriftMonitoringService | None = None
    chat_init_error: str | None = None
    chat_service: ChatService | None = None
    try:
        thresholds = DriftThresholds(
            data_warn=settings.drift_data_warn_threshold,
            data_critical=settings.drift_data_critical_threshold,
            concept_warn=settings.drift_concept_warn_threshold,
            concept_critical=settings.drift_concept_critical_threshold,
            target_warn=settings.drift_target_warn_threshold,
            target_critical=settings.drift_target_critical_threshold,
        )
        drift_service = DriftMonitoringService(
            thresholds=thresholds,
            window_size=settings.drift_window_size,
            min_samples=settings.drift_min_samples,
            baseline_stats=_load_drift_baseline_stats(settings.drift_baseline_path),
        )
    except (RuntimeError, ValueError) as exc:
        drift_init_error = str(exc)

    try:
        llm_client = OpenRouterLLMClient(settings)
        chat_service = ChatService(
            predictor=predictor,
            llm_service=llm_client,
            history_repository=history_repository,
            drift_service=drift_service,
            prediction_feed_service=prediction_feed_service,
        )
    except RuntimeError as exc:
        chat_init_error = str(exc)

    return AppContainer(
        settings=settings,
        predictor=predictor,
        drift_service=drift_service,
        prediction_feed_service=prediction_feed_service,
        chat_service=chat_service,
        drift_init_error=drift_init_error,
        chat_init_error=chat_init_error,
    )


def create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = build_container(settings)
        yield
        app.state.container = None

    return lifespan
