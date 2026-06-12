from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from core.exceptions import NotFoundError, ValidationError
from modules.asset.repositories.asset_repository import AssetRepository
from modules.portfolio.repositories.portfolio_repository import PortfolioRepository
from modules.trade.models.trade import Trade
from modules.trade.repositories import TradeRepository
from modules.trade.schemas import RegisterTradeRequest, TradeResponse, UpdateTradeRequest
from modules.trade.services.position_engine import replay_trades
from modules.trade.services.position_service import PositionService


class TradeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trade_repository = TradeRepository(db)
        self.portfolio_repository = PortfolioRepository(db)
        self.asset_repository = AssetRepository(db)
        self.position_service = PositionService(db)

    def register_trade(
        self,
        user_id: int,
        portfolio_id: int,
        request: RegisterTradeRequest,
    ) -> TradeResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        self._ensure_asset_exists(request.asset_id)

        trade = Trade(
            portfolio_id=portfolio_id,
            asset_id=request.asset_id,
            trade_type=request.trade_type,
            quantity=request.quantity,
            price=request.price,
            fees=request.fees,
            executed_at=request.executed_at,
            notes=request.notes,
        )
        self._validate_trade_sequence(portfolio_id, request.asset_id, trade)

        created_trade = self.trade_repository.create(trade)
        self.position_service.recalculate_position(portfolio_id, request.asset_id)
        self.db.commit()
        self.db.refresh(created_trade)
        return TradeResponse.model_validate(created_trade)

    def update_trade(
        self,
        user_id: int,
        portfolio_id: int,
        trade_id: int,
        request: UpdateTradeRequest,
    ) -> TradeResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        trade = self._get_trade(portfolio_id, trade_id)
        original_asset_id = trade.asset_id
        update_data = request.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields provided for update")

        if "asset_id" in update_data and update_data["asset_id"] is not None:
            self._ensure_asset_exists(update_data["asset_id"])
            trade.asset_id = update_data["asset_id"]

        if "trade_type" in update_data and update_data["trade_type"] is not None:
            trade.trade_type = update_data["trade_type"]

        if "quantity" in update_data and update_data["quantity"] is not None:
            trade.quantity = update_data["quantity"]

        if "price" in update_data and update_data["price"] is not None:
            trade.price = update_data["price"]

        if "fees" in update_data and update_data["fees"] is not None:
            trade.fees = update_data["fees"]

        if "executed_at" in update_data and update_data["executed_at"] is not None:
            trade.executed_at = update_data["executed_at"]

        if "notes" in update_data:
            trade.notes = update_data["notes"]

        self._validate_trade_sequence(
            portfolio_id,
            trade.asset_id,
            trade,
            exclude_trade_id=trade.id,
        )

        updated_trade = self.trade_repository.update(trade)
        self.position_service.recalculate_position(portfolio_id, trade.asset_id)

        if original_asset_id != trade.asset_id:
            self.position_service.recalculate_position(portfolio_id, original_asset_id)

        self.db.commit()
        self.db.refresh(updated_trade)
        return TradeResponse.model_validate(updated_trade)

    def delete_trade(self, user_id: int, portfolio_id: int, trade_id: int) -> None:
        self._ensure_portfolio_access(user_id, portfolio_id)
        trade = self._get_trade(portfolio_id, trade_id)
        asset_id = trade.asset_id

        self.trade_repository.delete(trade)
        self.position_service.recalculate_position(portfolio_id, asset_id)
        self.db.commit()

    def get_trade(self, user_id: int, portfolio_id: int, trade_id: int) -> TradeResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        trade = self._get_trade(portfolio_id, trade_id)
        return TradeResponse.model_validate(trade)

    def list_trades(self, user_id: int, portfolio_id: int) -> list[TradeResponse]:
        self._ensure_portfolio_access(user_id, portfolio_id)
        trades = self.trade_repository.list_by_portfolio_id(portfolio_id)
        return [TradeResponse.model_validate(trade) for trade in trades]

    def _get_trade(self, portfolio_id: int, trade_id: int) -> Trade:
        trade = self.trade_repository.get_by_id_and_portfolio_id(trade_id, portfolio_id)
        if trade is None:
            raise NotFoundError("Trade not found")
        return trade

    def _ensure_portfolio_access(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self.portfolio_repository.get_by_id_and_user_id(portfolio_id, user_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found")

    def _ensure_asset_exists(self, asset_id: int) -> None:
        asset = self.asset_repository.get_by_id(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")

    def _validate_trade_sequence(
        self,
        portfolio_id: int,
        asset_id: int,
        candidate_trade: Trade,
        *,
        exclude_trade_id: int | None = None,
    ) -> None:
        trades = self.trade_repository.list_by_portfolio_and_asset(portfolio_id, asset_id)
        sequence = [trade for trade in trades if trade.id != exclude_trade_id]

        validation_trade = Trade(
            id=max([trade.id for trade in trades], default=0) + 1,
            portfolio_id=candidate_trade.portfolio_id,
            asset_id=candidate_trade.asset_id,
            trade_type=candidate_trade.trade_type,
            quantity=candidate_trade.quantity,
            price=candidate_trade.price,
            fees=candidate_trade.fees,
            executed_at=candidate_trade.executed_at,
            notes=candidate_trade.notes,
        )
        sequence.append(validation_trade)
        replay_trades(sequence)
