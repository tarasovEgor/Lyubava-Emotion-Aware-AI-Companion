from typing import Annotated

from fastapi import Depends, Request

from lyubava.api.services.chat import ChatService
from lyubava.api.services.prediction_feed import PredictionFeedService
from lyubava.core.errors import ServiceUnavailableError
from lyubava.core.lifecycle import AppContainer
from lyubava.models.predict import EmotionPredictor
from lyubava.monitoring.service import DriftMonitoringService


def get_container(request: Request) -> AppContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise ServiceUnavailableError("Application services are not initialized.")
    return container


def get_predictor(
    container: Annotated[AppContainer, Depends(get_container)],
) -> EmotionPredictor:
    return container.predictor


def get_chat_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> ChatService:
    if container.chat_service is None:
        raise ServiceUnavailableError(
            container.chat_init_error or "Chat service is not ready."
        )
    return container.chat_service


def get_drift_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> DriftMonitoringService:
    if container.drift_service is None:
        raise ServiceUnavailableError(
            container.drift_init_error or "Drift monitoring service is not ready."
        )
    return container.drift_service


def get_prediction_feed_service(
    container: Annotated[AppContainer, Depends(get_container)],
) -> PredictionFeedService:
    return container.prediction_feed_service
