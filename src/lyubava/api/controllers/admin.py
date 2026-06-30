from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from lyubava.api.dependencies import get_prediction_feed_service, get_retrain_service
from lyubava.api.schemas import AdminPredictionsResponse, RetrainStatusResponse
from lyubava.api.services.prediction_feed import PredictionFeedService
from lyubava.api.services.retrain import RetrainService

router = APIRouter(tags=["admin"])


@router.get("/admin/predictions", response_model=AdminPredictionsResponse)
def get_admin_predictions(
    feed_service: Annotated[
        PredictionFeedService, Depends(get_prediction_feed_service)
    ],
    limit: int = Query(50, ge=1, le=200),
) -> AdminPredictionsResponse:
    return AdminPredictionsResponse(items=feed_service.list_items(limit))


@router.post(
    "/admin/retrain",
    response_model=RetrainStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_admin_retrain(
    retrain_service: Annotated[RetrainService, Depends(get_retrain_service)],
) -> RetrainStatusResponse:
    return RetrainStatusResponse.model_validate(
        retrain_service.start(),
        from_attributes=True,
    )


@router.get("/admin/retrain", response_model=RetrainStatusResponse)
def get_admin_retrain_status(
    retrain_service: Annotated[RetrainService, Depends(get_retrain_service)],
) -> RetrainStatusResponse:
    return RetrainStatusResponse.model_validate(
        retrain_service.get_status(),
        from_attributes=True,
    )
