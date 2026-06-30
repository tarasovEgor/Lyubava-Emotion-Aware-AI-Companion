from typing import Annotated

from fastapi import APIRouter, Depends

from lyubava.api.dependencies import get_predictor
from lyubava.api.schemas import EmotionRequest, EmotionResponse
from lyubava.models.predict import EmotionPredictor

router = APIRouter(tags=["emotion"])


@router.post("/predict-emotion", response_model=EmotionResponse)
def predict_emotion(
    payload: EmotionRequest,
    predictor: Annotated[EmotionPredictor, Depends(get_predictor)],
) -> EmotionResponse:
    result = predictor.predict(payload.text)
    return EmotionResponse(
        emotion=result["emotion"],
        confidence=result["confidence"],
    )
