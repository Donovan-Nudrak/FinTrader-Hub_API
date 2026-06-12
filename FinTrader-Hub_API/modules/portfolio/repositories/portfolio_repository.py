from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.portfolio.models.portfolio import Portfolio


class PortfolioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, portfolio: Portfolio) -> Portfolio:
        self.db.add(portfolio)
        self.db.flush()
        self.db.refresh(portfolio)
        return portfolio

    def get_by_id_and_user_id(self, portfolio_id: int, user_id: int) -> Portfolio | None:
        statement = select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
        return self.db.scalar(statement)

    def list_by_user_id(self, user_id: int) -> list[Portfolio]:
        statement = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update(self, portfolio: Portfolio) -> Portfolio:
        self.db.add(portfolio)
        self.db.flush()
        self.db.refresh(portfolio)
        return portfolio

    def delete(self, portfolio: Portfolio) -> None:
        self.db.delete(portfolio)
        self.db.flush()
