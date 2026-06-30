from typing import Annotated, Any

from fastapi import APIRouter, Depends

from lyubava.api.dependencies import get_drift_service
from lyubava.monitoring.service import DriftMonitoringService

router = APIRouter(tags=["monitoring"])


@router.get("/monitoring/drift")
def get_drift_snapshot(
    drift_service: Annotated[DriftMonitoringService, Depends(get_drift_service)],
) -> dict[str, Any]:
    return drift_service.snapshot()
