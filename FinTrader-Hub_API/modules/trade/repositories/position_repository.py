from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.trade.models.position import Position


class PositionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, position: Position) -> Position:
        self.db.add(position)
        self.db.flush()
        self.db.refresh(position)
        return position

    def get_by_id_and_portfolio_id(self, position_id: int, portfolio_id: int) -> Position | None:
        statement = select(Position).where(
            Position.id == position_id,
            Position.portfolio_id == portfolio_id,
        )
        return self.db.scalar(statement)

    def get_by_portfolio_and_asset(self, portfolio_id: int, asset_id: int) -> Position | None:
        statement = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
        return self.db.scalar(statement)

    def list_by_portfolio_id(self, portfolio_id: int) -> list[Position]:
        statement = (
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .order_by(Position.opened_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update(self, position: Position) -> Position:
        self.db.add(position)
        self.db.flush()
        self.db.refresh(position)
        return position

    def delete(self, position: Position) -> None:
        self.db.delete(position)
        self.db.flush()
