from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from lyubava.api.controllers import api_v1_router
from lyubava.core.config import Settings
from lyubava.core.errors import AppError
from lyubava.core.lifecycle import create_lifespan
from lyubava.monitoring import metrics as _monitoring_metrics

load_dotenv()


def create_app() -> FastAPI:
    settings = Settings.from_env()
    app = FastAPI(
        title="Lyubava Emotion API",
        description="Emotion classification service for the Lyubava AI companion.",
        version="0.1.0",
        lifespan=create_lifespan(settings),
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        _ = _monitoring_metrics
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(api_v1_router)
    return app


app = create_app()
