import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from lyubava.api.schemas import EmotionRequest, EmotionResponse, HealthResponse
from lyubava.models.predict import EmotionPredictor


DEFAULT_MODEL_DIR = "models/emotion_classifier"

predictor: EmotionPredictor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the model once when the API process starts.

    Important:
    - Do not load the model inside the request handler.
    - In Docker/Kubernetes, MODEL_DIR can point to a copied or mounted model artifact.
    """
    global predictor

    model_dir = os.getenv("MODEL_DIR", DEFAULT_MODEL_DIR)
    predictor = EmotionPredictor(model_dir)

    yield

    predictor = None


app = FastAPI(
    title="Lyubava Emotion API",
    description="Emotion classification service for the Lyubava AI companion.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded.",
        )

    return HealthResponse(status="ready")


@app.post("/predict-emotion", response_model=EmotionResponse)
def predict_emotion(payload: EmotionRequest) -> EmotionResponse:
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded.",
        )

    try:
        result = predictor.predict(payload.text)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed.",
        ) from exc

    return EmotionResponse(
        emotion=result["emotion"],
        confidence=result["confidence"],
    )