from fastapi import APIRouter

from lyubava.api.controllers import chat, emotion, health

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(emotion.router)
api_v1_router.include_router(chat.router)
