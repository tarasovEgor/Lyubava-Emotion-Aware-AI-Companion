from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        examples=["session-123"],
    )
    message: str = Field(
        ...,
        min_length=1,
        examples=["Мне очень тревожно, я не знаю что делать."],
    )


class ChatDebug(BaseModel):
    provider: str
    model: str
    system_prompt: str
    history_length: int = Field(..., ge=0)
    usage: dict[str, int] | None = None
    response_metadata: dict[str, str | int | float | bool | None] | None = None


class ChatResponse(BaseModel):
    reply: str
    emotion: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    debug: ChatDebug


class ChatHistoryMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatHistoryMessage]


class ChatResetRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        examples=["session-123"],
    )


class ChatResetResponse(BaseModel):
    status: str
    session_id: str
