from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from modules.alerts.models.alert_event import AlertEvent


class AlertEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, alert_event: AlertEvent) -> AlertEvent:
        self.db.add(alert_event)
        self.db.flush()
        self.db.refresh(alert_event)
        return alert_event

    def list_by_alert_id(self, alert_id: int) -> list[AlertEvent]:
        statement = (
            select(AlertEvent)
            .options(joinedload(AlertEvent.notification))
            .where(AlertEvent.alert_id == alert_id)
            .order_by(AlertEvent.triggered_at.desc(), AlertEvent.id.desc())
        )
        return list(self.db.scalars(statement).all())
