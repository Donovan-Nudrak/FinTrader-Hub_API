from typing import Annotated

from fastapi import APIRouter, Depends, status

from core.schemas import APIResponse
from modules.alerts.dependencies import get_alert_service
from modules.alerts.schemas import (
    AlertEventResponse,
    AlertResponse,
    CreateAlertRequest,
    EvaluateAlertResponse,
    UpdateAlertRequest,
)
from modules.alerts.services import AlertService
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=APIResponse[AlertResponse], status_code=status.HTTP_201_CREATED)
def create_alert(
    request: CreateAlertRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[AlertResponse]:
    alert = alert_service.create_alert(current_user.id, request)
    return APIResponse(message="Alert created successfully", data=alert)


@router.get("", response_model=APIResponse[list[AlertResponse]])
def list_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[list[AlertResponse]]:
    alerts = alert_service.list_alerts(current_user.id)
    return APIResponse(message="Alerts retrieved successfully", data=alerts)


@router.get("/{alert_id}", response_model=APIResponse[AlertResponse])
def get_alert(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[AlertResponse]:
    alert = alert_service.get_alert(current_user.id, alert_id)
    return APIResponse(message="Alert retrieved successfully", data=alert)


@router.put("/{alert_id}", response_model=APIResponse[AlertResponse])
def update_alert(
    alert_id: int,
    request: UpdateAlertRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[AlertResponse]:
    alert = alert_service.update_alert(current_user.id, alert_id, request)
    return APIResponse(message="Alert updated successfully", data=alert)


@router.delete("/{alert_id}", response_model=APIResponse[None])
def delete_alert(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[None]:
    alert_service.delete_alert(current_user.id, alert_id)
    return APIResponse(message="Alert deleted successfully", data=None)


@router.get("/{alert_id}/history", response_model=APIResponse[list[AlertEventResponse]])
def get_alert_history(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[list[AlertEventResponse]]:
    history = alert_service.get_alert_history(current_user.id, alert_id)
    return APIResponse(message="Alert history retrieved successfully", data=history)


@router.post("/{alert_id}/evaluate", response_model=APIResponse[EvaluateAlertResponse])
def evaluate_alert(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> APIResponse[EvaluateAlertResponse]:
    result = alert_service.evaluate_alert(current_user.id, alert_id)
    return APIResponse(message="Alert evaluated successfully", data=result)
