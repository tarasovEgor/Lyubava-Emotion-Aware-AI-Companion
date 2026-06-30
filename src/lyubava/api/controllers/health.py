from typing import Annotated

from fastapi import APIRouter, Depends

from lyubava.api.dependencies import get_predictor
from lyubava.api.schemas import HealthResponse
from lyubava.models.predict import EmotionPredictor

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
def ready(
    _: Annotated[EmotionPredictor, Depends(get_predictor)],
) -> HealthResponse:
    return HealthResponse(status="ready")
