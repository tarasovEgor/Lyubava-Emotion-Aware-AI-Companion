from pydantic import BaseModel, Field


class EmotionRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        examples=["I feel really lonely today."],
    )


class EmotionResponse(BaseModel):
    emotion: str
    confidence: float = Field(..., ge=0.0, le=1.0)
