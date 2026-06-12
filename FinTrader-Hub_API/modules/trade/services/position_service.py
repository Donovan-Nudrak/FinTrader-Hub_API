from sqlalchemy.orm import Session

from core.exceptions import NotFoundError, ValidationError
from modules.portfolio.repositories.portfolio_repository import PortfolioRepository
from modules.trade.models.position import Position
from modules.trade.repositories import PositionRepository, TradeRepository
from modules.trade.schemas import PositionResponse
from modules.trade.services.position_engine import replay_trades


class PositionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.position_repository = PositionRepository(db)
        self.trade_repository = TradeRepository(db)
        self.portfolio_repository = PortfolioRepository(db)

    def get_position(self, user_id: int, portfolio_id: int, position_id: int) -> PositionResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        position = self.position_repository.get_by_id_and_portfolio_id(position_id, portfolio_id)
        if position is None:
            raise NotFoundError("Position not found")
        return PositionResponse.model_validate(position)

    def list_portfolio_positions(self, user_id: int, portfolio_id: int) -> list[PositionResponse]:
        self._ensure_portfolio_access(user_id, portfolio_id)
        positions = self.position_repository.list_by_portfolio_id(portfolio_id)
        return [PositionResponse.model_validate(position) for position in positions]

    def recalculate_position(self, portfolio_id: int, asset_id: int) -> Position | None:
        trades = self.trade_repository.list_by_portfolio_and_asset(portfolio_id, asset_id)
        existing_position = self.position_repository.get_by_portfolio_and_asset(portfolio_id, asset_id)

        if not trades:
            if existing_position is not None:
                self.position_repository.delete(existing_position)
                self.trade_repository.sync_position_ids(portfolio_id, asset_id, None)
            return None

        calculated = replay_trades(trades)

        if calculated is None:
            if existing_position is not None:
                self.position_repository.delete(existing_position)
                self.trade_repository.sync_position_ids(portfolio_id, asset_id, None)
            return None

        if existing_position is None:
            position = Position(
                portfolio_id=portfolio_id,
                asset_id=asset_id,
                position_type=calculated.position_type,
                quantity=calculated.quantity,
                average_price=calculated.average_price,
                total_cost=calculated.total_cost,
                status=calculated.status,
                opened_at=calculated.opened_at,
                closed_at=calculated.closed_at,
            )
            saved_position = self.position_repository.create(position)
        else:
            existing_position.position_type = calculated.position_type
            existing_position.quantity = calculated.quantity
            existing_position.average_price = calculated.average_price
            existing_position.total_cost = calculated.total_cost
            existing_position.status = calculated.status
            existing_position.opened_at = calculated.opened_at
            existing_position.closed_at = calculated.closed_at
            saved_position = self.position_repository.update(existing_position)

        self.trade_repository.sync_position_ids(portfolio_id, asset_id, saved_position.id)
        return saved_position

    def recalculate_position_for_user(
        self,
        user_id: int,
        portfolio_id: int,
        asset_id: int,
    ) -> PositionResponse | None:
        self._ensure_portfolio_access(user_id, portfolio_id)
        position = self.recalculate_position(portfolio_id, asset_id)
        self.db.commit()
        if position is None:
            return None
        return PositionResponse.model_validate(position)

    def _ensure_portfolio_access(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self.portfolio_repository.get_by_id_and_user_id(portfolio_id, user_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found")
