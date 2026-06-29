from pydantic import BaseModel, Field


class PredictionRow(BaseModel):
    timestamp: str
    session_id: str
    text: str
    predicted_emotion: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    model: str
    provider: str


class AdminPredictionsResponse(BaseModel):
    items: list[PredictionRow]
