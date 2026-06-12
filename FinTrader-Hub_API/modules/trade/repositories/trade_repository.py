from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.trade.models.trade import Trade


class TradeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, trade: Trade) -> Trade:
        self.db.add(trade)
        self.db.flush()
        self.db.refresh(trade)
        return trade

    def get_by_id_and_portfolio_id(self, trade_id: int, portfolio_id: int) -> Trade | None:
        statement = select(Trade).where(
            Trade.id == trade_id,
            Trade.portfolio_id == portfolio_id,
        )
        return self.db.scalar(statement)

    def list_by_portfolio_id(self, portfolio_id: int) -> list[Trade]:
        statement = (
            select(Trade)
            .where(Trade.portfolio_id == portfolio_id)
            .order_by(Trade.executed_at.desc(), Trade.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_by_portfolio_and_asset(self, portfolio_id: int, asset_id: int) -> list[Trade]:
        statement = (
            select(Trade)
            .where(
                Trade.portfolio_id == portfolio_id,
                Trade.asset_id == asset_id,
            )
            .order_by(Trade.executed_at.asc(), Trade.id.asc())
        )
        return list(self.db.scalars(statement).all())

    def update(self, trade: Trade) -> Trade:
        self.db.add(trade)
        self.db.flush()
        self.db.refresh(trade)
        return trade

    def delete(self, trade: Trade) -> None:
        self.db.delete(trade)
        self.db.flush()

    def sync_position_ids(self, portfolio_id: int, asset_id: int, position_id: int | None) -> None:
        trades = self.list_by_portfolio_and_asset(portfolio_id, asset_id)
        for trade in trades:
            trade.position_id = position_id
            self.db.add(trade)
        self.db.flush()
