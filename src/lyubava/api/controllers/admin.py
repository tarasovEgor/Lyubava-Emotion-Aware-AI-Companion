from typing import Annotated

from fastapi import APIRouter, Depends, Query

from lyubava.api.dependencies import get_prediction_feed_service
from lyubava.api.schemas import AdminPredictionsResponse
from lyubava.api.services.prediction_feed import PredictionFeedService

router = APIRouter(tags=["admin"])


@router.get("/admin/predictions", response_model=AdminPredictionsResponse)
def get_admin_predictions(
    feed_service: Annotated[
        PredictionFeedService, Depends(get_prediction_feed_service)
    ],
    limit: int = Query(50, ge=1, le=200),
) -> AdminPredictionsResponse:
    return AdminPredictionsResponse(items=feed_service.list_items(limit))
