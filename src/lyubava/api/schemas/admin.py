from typing import Any, Literal

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


class RetrainStatusResponse(BaseModel):
    state: Literal["idle", "running", "succeeded", "failed"]
    started_at: str | None = None
    finished_at: str | None = None
    message: str | None = None
    metrics: dict[str, Any] | None = None
