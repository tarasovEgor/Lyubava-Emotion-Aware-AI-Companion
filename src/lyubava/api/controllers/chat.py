from typing import Annotated

from fastapi import APIRouter, Depends, Query

from lyubava.api.dependencies import get_chat_service
from lyubava.api.schemas import (
    ChatDebug,
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatRequest,
    ChatResetRequest,
    ChatResetResponse,
    ChatResponse,
)
from lyubava.api.services.chat import ChatService


router = APIRouter(tags=["chat"])


@router.get("/chat/messages", response_model=ChatHistoryResponse)
def get_chat_messages(
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    session_id: str = Query(..., min_length=1),
) -> ChatHistoryResponse:
    messages = chat_service.get_session_history(session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatHistoryMessage(
                id=item.id,
                role=item.role.value,
                content=item.content,
                created_at=item.created_at,
            )
            for item in messages
        ],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    emotion_result, llm_reply, history_length = chat_service.respond(
        session_id=payload.session_id,
        message=payload.message,
    )
    return ChatResponse(
        reply=llm_reply.text,
        emotion=emotion_result["emotion"],
        confidence=emotion_result["confidence"],
        debug=ChatDebug(
            provider=llm_reply.provider,
            model=llm_reply.model,
            system_prompt=llm_reply.system_prompt,
            history_length=history_length,
            usage=llm_reply.usage,
            response_metadata=llm_reply.response_metadata,
        ),
    )


@router.post("/chat/reset", response_model=ChatResetResponse)
def reset_chat(
    payload: ChatResetRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResetResponse:
    chat_service.reset_session(payload.session_id)
    return ChatResetResponse(status="reset", session_id=payload.session_id)
