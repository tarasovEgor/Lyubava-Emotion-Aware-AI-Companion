from fastapi import APIRouter

from lyubava.api.controllers import admin, chat, emotion, health, monitoring

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(emotion.router)
api_v1_router.include_router(chat.router)
api_v1_router.include_router(monitoring.router)
api_v1_router.include_router(admin.router)
