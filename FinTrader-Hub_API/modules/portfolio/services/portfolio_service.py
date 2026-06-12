from sqlalchemy.orm import Session

from core.exceptions import NotFoundError, ValidationError
from modules.portfolio.models.portfolio import Portfolio
from modules.portfolio.repositories import PortfolioRepository
from modules.portfolio.schemas import (
    CreatePortfolioRequest,
    PortfolioResponse,
    UpdatePortfolioRequest,
)


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portfolio_repository = PortfolioRepository(db)

    def create_portfolio(self, user_id: int, request: CreatePortfolioRequest) -> PortfolioResponse:
        portfolio = Portfolio(
            user_id=user_id,
            name=request.name.strip(),
            description=request.description,
            base_currency=request.base_currency.upper(),
            is_active=True,
        )
        created = self.portfolio_repository.create(portfolio)
        self.db.commit()
        return PortfolioResponse.model_validate(created)

    def update_portfolio(
        self,
        user_id: int,
        portfolio_id: int,
        request: UpdatePortfolioRequest,
    ) -> PortfolioResponse:
        portfolio = self._get_owned_portfolio(user_id, portfolio_id)
        update_data = request.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields provided for update")

        if "name" in update_data and update_data["name"] is not None:
            portfolio.name = update_data["name"].strip()

        if "description" in update_data:
            portfolio.description = update_data["description"]

        if "base_currency" in update_data and update_data["base_currency"] is not None:
            portfolio.base_currency = update_data["base_currency"].upper()

        if "is_active" in update_data and update_data["is_active"] is not None:
            portfolio.is_active = update_data["is_active"]

        updated = self.portfolio_repository.update(portfolio)
        self.db.commit()
        return PortfolioResponse.model_validate(updated)

    def delete_portfolio(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self._get_owned_portfolio(user_id, portfolio_id)
        self.portfolio_repository.delete(portfolio)
        self.db.commit()

    def get_portfolio(self, user_id: int, portfolio_id: int) -> PortfolioResponse:
        portfolio = self._get_owned_portfolio(user_id, portfolio_id)
        return PortfolioResponse.model_validate(portfolio)

    def list_portfolios(self, user_id: int) -> list[PortfolioResponse]:
        portfolios = self.portfolio_repository.list_by_user_id(user_id)
        return [PortfolioResponse.model_validate(portfolio) for portfolio in portfolios]

    def _get_owned_portfolio(self, user_id: int, portfolio_id: int) -> Portfolio:
        portfolio = self.portfolio_repository.get_by_id_and_user_id(portfolio_id, user_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found")
        return portfolio
