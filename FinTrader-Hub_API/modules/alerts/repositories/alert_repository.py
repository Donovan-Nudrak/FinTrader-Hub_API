from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.alerts.models.alert import Alert


class AlertRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.flush()
        self.db.refresh(alert)
        return alert

    def update(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.flush()
        self.db.refresh(alert)
        return alert

    def delete(self, alert: Alert) -> None:
        self.db.delete(alert)
        self.db.flush()

    def get_by_id_and_user_id(self, alert_id: int, user_id: int) -> Alert | None:
        statement = select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
        return self.db.scalar(statement)

    def list_by_user_id(self, user_id: int) -> list[Alert]:
        statement = (
            select(Alert)
            .where(Alert.user_id == user_id)
            .order_by(Alert.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_active(self) -> list[Alert]:
        statement = (
            select(Alert)
            .where(Alert.is_active.is_(True))
            .order_by(Alert.id.asc())
        )
        return list(self.db.scalars(statement).all())
