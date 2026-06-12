import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from core.config import get_settings
from core.enums import AlertCondition, AlertType, NotificationChannel, NotificationStatus
from core.exceptions import NotFoundError, ValidationError
from infrastructure.notifications.email.resend_client import ResendClient
from modules.alerts.models.alert import Alert
from modules.alerts.models.alert_event import AlertEvent
from modules.alerts.models.notification import Notification
from modules.alerts.repositories import AlertEventRepository, AlertRepository, NotificationRepository
from modules.alerts.schemas.alert import (
    AlertEventResponse,
    AlertResponse,
    CreateAlertRequest,
    EvaluateAlertResponse,
    NotificationResponse,
    UpdateAlertRequest,
)
from modules.alerts.services.alert_evaluator import (
    evaluate_alert_condition,
    is_within_cooldown,
)
from modules.asset.repositories.asset_repository import AssetRepository
from modules.market.repositories.market_price_repository import MarketPriceRepository
from modules.portfolio.repositories import PortfolioRepository
from modules.portfolio.services.analytics_service import AnalyticsService
from modules.risk.services.risk_service import RiskService


class AlertService:
    def __init__(self, db: Session, resend_client: ResendClient | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        self.alert_repository = AlertRepository(db)
        self.alert_event_repository = AlertEventRepository(db)
        self.notification_repository = NotificationRepository(db)
        self.portfolio_repository = PortfolioRepository(db)
        self.asset_repository = AssetRepository(db)
        self.market_price_repository = MarketPriceRepository(db)
        self.analytics_service = AnalyticsService(db)
        self.risk_service = RiskService(db)
        self.resend_client = resend_client or ResendClient()

    def create_alert(self, user_id: int, request: CreateAlertRequest) -> AlertResponse:
        self._validate_alert_request(user_id, request.alert_type, request.condition, request.asset_id, request.portfolio_id)

        alert = Alert(
            user_id=user_id,
            asset_id=request.asset_id,
            portfolio_id=request.portfolio_id,
            alert_type=request.alert_type,
            condition=request.condition,
            threshold=request.threshold,
            is_active=request.is_active,
        )
        created = self.alert_repository.create(alert)
        self.db.commit()
        return AlertResponse.model_validate(created)

    def update_alert(
        self,
        user_id: int,
        alert_id: int,
        request: UpdateAlertRequest,
    ) -> AlertResponse:
        alert = self._get_owned_alert(user_id, alert_id)
        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided for update")

        alert_type = update_data.get("alert_type", alert.alert_type)
        condition = update_data.get("condition", alert.condition)
        asset_id = update_data.get("asset_id", alert.asset_id)
        portfolio_id = update_data.get("portfolio_id", alert.portfolio_id)
        self._validate_alert_request(user_id, alert_type, condition, asset_id, portfolio_id)

        for field, value in update_data.items():
            setattr(alert, field, value)

        updated = self.alert_repository.update(alert)
        self.db.commit()
        return AlertResponse.model_validate(updated)

    def delete_alert(self, user_id: int, alert_id: int) -> None:
        alert = self._get_owned_alert(user_id, alert_id)
        self.alert_repository.delete(alert)
        self.db.commit()

    def get_alert(self, user_id: int, alert_id: int) -> AlertResponse:
        alert = self._get_owned_alert(user_id, alert_id)
        return AlertResponse.model_validate(alert)

    def list_alerts(self, user_id: int) -> list[AlertResponse]:
        alerts = self.alert_repository.list_by_user_id(user_id)
        return [AlertResponse.model_validate(alert) for alert in alerts]

    def get_alert_history(self, user_id: int, alert_id: int) -> list[AlertEventResponse]:
        alert = self._get_owned_alert(user_id, alert_id)
        events = self.alert_event_repository.list_by_alert_id(alert.id)
        return [self._to_alert_event_response(event) for event in events]

    def evaluate_alert(self, user_id: int, alert_id: int) -> EvaluateAlertResponse:
        alert = self._get_owned_alert(user_id, alert_id)
        return self._evaluate_and_trigger(alert)

    def evaluate_all_active_alerts(self) -> dict[str, int]:
        alerts = self.alert_repository.list_active()
        triggered_count = 0
        evaluated_count = 0
        failed_count = 0

        logger.info("Starting alert evaluation for %s active alerts", len(alerts))

        for alert in alerts:
            try:
                result = self._evaluate_and_trigger(alert)
                evaluated_count += 1
                if result.triggered:
                    triggered_count += 1
                    logger.info(
                        "Alert triggered",
                        extra={"alert_id": alert.id, "trigger_value": result.trigger_value},
                    )
            except Exception as exc:
                failed_count += 1
                self.db.rollback()
                logger.error(
                    "Failed to evaluate alert",
                    extra={"alert_id": alert.id},
                    exc_info=exc,
                )

        summary = {
            "evaluated": evaluated_count,
            "triggered": triggered_count,
            "failed": failed_count,
        }
        logger.info("Alert evaluation finished", extra={"result": summary})
        return summary

    def _evaluate_and_trigger(self, alert: Alert) -> EvaluateAlertResponse:
        now = datetime.now(UTC)

        if is_within_cooldown(alert.last_triggered_at, now):
            return EvaluateAlertResponse(
                alert_id=alert.id,
                evaluated=True,
                triggered=False,
                cooldown_active=True,
                message="Alert is within the 24-hour cooldown period",
            )

        try:
            current_value, base_value = self._resolve_metric_values(alert)
        except ValidationError as exc:
            return EvaluateAlertResponse(
                alert_id=alert.id,
                evaluated=True,
                triggered=False,
                message=exc.message,
            )

        evaluation = evaluate_alert_condition(
            alert.alert_type,
            alert.condition,
            float(alert.threshold),
            current_value,
            base_value=base_value,
        )

        if not evaluation.triggered:
            return EvaluateAlertResponse(
                alert_id=alert.id,
                evaluated=True,
                triggered=False,
                trigger_value=Decimal(str(evaluation.trigger_value)),
                message=evaluation.message,
            )

        alert_event = self._trigger_alert(alert, evaluation.trigger_value, evaluation.message, now)
        return EvaluateAlertResponse(
            alert_id=alert.id,
            evaluated=True,
            triggered=True,
            trigger_value=Decimal(str(evaluation.trigger_value)),
            message=evaluation.message,
            alert_event_id=alert_event.id,
        )

    def _trigger_alert(
        self,
        alert: Alert,
        trigger_value: float,
        message: str,
        triggered_at: datetime,
    ) -> AlertEvent:
        alert_event = AlertEvent(
            alert_id=alert.id,
            triggered_at=triggered_at,
            trigger_value=Decimal(str(trigger_value)),
            message=message,
        )
        created_event = self.alert_event_repository.create(alert_event)

        notification = Notification(
            alert_event_id=created_event.id,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
        )
        created_notification = self.notification_repository.create(notification)

        subject = f"FinTrader Hub Alert: {alert.alert_type.value}"
        body = (
            f"Alert ID: {alert.id}\n"
            f"Type: {alert.alert_type.value}\n"
            f"Condition: {alert.condition.value}\n"
            f"Threshold: {alert.threshold}\n\n"
            f"{message}"
        )
        sent = self.resend_client.send_alert_email(
            subject=subject,
            body=body,
            to_email=self.settings.alert_email,
        )

        if sent:
            created_notification.status = NotificationStatus.SENT
            created_notification.sent_at = triggered_at
        else:
            created_notification.status = NotificationStatus.FAILED
            created_notification.error_message = "Email delivery failed"

        self.notification_repository.update(created_notification)
        alert.last_triggered_at = triggered_at
        self.alert_repository.update(alert)
        self.db.commit()
        return created_event

    def _resolve_metric_values(self, alert: Alert) -> tuple[float, float | None]:
        if alert.alert_type == AlertType.PRICE:
            if alert.asset_id is None:
                raise ValidationError("Price alerts require asset_id")

            latest = self.market_price_repository.get_latest_by_asset_id(alert.asset_id)
            if latest is None:
                raise ValidationError("No market price available for asset")

            current_value = float(latest.price)
            base_value = self._resolve_price_base_value(alert.asset_id, latest.timestamp)
            return current_value, base_value

        if alert.portfolio_id is None:
            raise ValidationError("Portfolio alerts require portfolio_id")

        if alert.alert_type == AlertType.PORTFOLIO_VALUE:
            portfolio_value = self.analytics_service.calculate_portfolio_value(
                alert.user_id,
                alert.portfolio_id,
            )
            return float(portfolio_value.portfolio_value), None

        if alert.alert_type == AlertType.PORTFOLIO_PNL:
            performance = self.analytics_service.calculate_portfolio_performance(
                alert.user_id,
                alert.portfolio_id,
            )
            return float(performance.total_pnl), None

        if alert.alert_type == AlertType.DRAWDOWN:
            drawdown = self.risk_service.calculate_drawdown(alert.user_id, alert.portfolio_id)
            if drawdown.current_drawdown is None:
                raise ValidationError("Drawdown data is insufficient")
            return float(drawdown.current_drawdown), None

        if alert.alert_type == AlertType.CONCENTRATION:
            exposure = self.risk_service.calculate_exposure(alert.user_id, alert.portfolio_id)
            return float(exposure.hhi), None

        raise ValidationError(f"Unsupported alert type: {alert.alert_type}")

    def _resolve_price_base_value(self, asset_id: int, latest_timestamp: datetime) -> float | None:
        to_date = latest_timestamp
        from_date = to_date - timedelta(days=30)
        prices = self.market_price_repository.list_by_asset_and_range(
            asset_id,
            from_date=from_date,
            to_date=to_date,
        )
        if len(prices) < 2:
            return None

        ordered = sorted(prices, key=lambda price: price.timestamp)
        return float(ordered[-2].price)

    def _validate_alert_request(
        self,
        user_id: int,
        alert_type: AlertType,
        condition: AlertCondition,
        asset_id: int | None,
        portfolio_id: int | None,
    ) -> None:
        if alert_type == AlertType.PRICE:
            if asset_id is None:
                raise ValidationError("Price alerts require asset_id")
            if self.asset_repository.get_by_id(asset_id) is None:
                raise ValidationError("Asset not found")
            if condition not in {AlertCondition.ABOVE, AlertCondition.BELOW, AlertCondition.PERCENT_CHANGE}:
                raise ValidationError("Invalid condition for price alerts")
            return

        if portfolio_id is None:
            raise ValidationError("Portfolio alerts require portfolio_id")

        portfolio = self.portfolio_repository.get_by_id_and_user_id(portfolio_id, user_id)
        if portfolio is None:
            raise ValidationError("Portfolio not found")

        if alert_type in {AlertType.PORTFOLIO_VALUE, AlertType.PORTFOLIO_PNL}:
            if condition not in {AlertCondition.ABOVE, AlertCondition.BELOW}:
                raise ValidationError("Portfolio alerts support ABOVE and BELOW conditions only")
            return

        if alert_type in {AlertType.DRAWDOWN, AlertType.CONCENTRATION}:
            if condition != AlertCondition.ABOVE:
                raise ValidationError(f"{alert_type.value} alerts only support ABOVE condition")

    def _get_owned_alert(self, user_id: int, alert_id: int) -> Alert:
        alert = self.alert_repository.get_by_id_and_user_id(alert_id, user_id)
        if alert is None:
            raise NotFoundError("Alert not found")
        return alert

    def _to_alert_event_response(self, event: AlertEvent) -> AlertEventResponse:
        notification = event.notification
        notification_response = None
        if notification is not None:
            notification_response = NotificationResponse.model_validate(notification)

        return AlertEventResponse(
            id=event.id,
            alert_id=event.alert_id,
            triggered_at=event.triggered_at,
            trigger_value=event.trigger_value,
            message=event.message,
            notification=notification_response,
            created_at=event.created_at,
        )
