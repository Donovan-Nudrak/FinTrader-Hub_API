from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from core.enums import AlertCondition, AlertType, NotificationChannel, NotificationStatus


class CreateAlertRequest(BaseModel):
    asset_id: int | None = Field(default=None, gt=0)
    portfolio_id: int | None = Field(default=None, gt=0)
    alert_type: AlertType
    condition: AlertCondition
    threshold: Decimal = Field(gt=0)
    is_active: bool = True


class UpdateAlertRequest(BaseModel):
    asset_id: int | None = Field(default=None, gt=0)
    portfolio_id: int | None = Field(default=None, gt=0)
    alert_type: AlertType | None = None
    condition: AlertCondition | None = None
    threshold: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("asset_id", "portfolio_id", mode="before")
    @classmethod
    def validate_optional_positive_ids(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("ID must be a positive integer")
        return value


class AlertResponse(BaseModel):
    id: int
    user_id: int
    asset_id: int | None
    portfolio_id: int | None
    alert_type: AlertType
    condition: AlertCondition
    threshold: Decimal
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: int
    alert_event_id: int
    channel: NotificationChannel
    status: NotificationStatus
    sent_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertEventResponse(BaseModel):
    id: int
    alert_id: int
    triggered_at: datetime
    trigger_value: Decimal
    message: str
    notification: NotificationResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluateAlertResponse(BaseModel):
    alert_id: int
    evaluated: bool
    triggered: bool
    trigger_value: Decimal | None = None
    message: str | None = None
    alert_event_id: int | None = None
    cooldown_active: bool = False
