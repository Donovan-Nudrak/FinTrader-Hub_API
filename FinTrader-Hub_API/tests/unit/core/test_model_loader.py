from sqlalchemy.orm import class_mapper, configure_mappers

from modules.auth.models.user import User
from modules.portfolio.models.portfolio import Portfolio
from infrastructure.database.model_loader import get_registered_model_names, load_all_models

EXPECTED_MODELS = {
    "Alert",
    "AlertEvent",
    "ApiKey",
    "Asset",
    "MarketPrice",
    "News",
    "Notification",
    "Portfolio",
    "Position",
    "RefreshToken",
    "Role",
    "Trade",
    "User",
    "UserSetting",
}


def test_load_all_models_registers_expected_mappers() -> None:
    load_all_models()

    registered = get_registered_model_names()
    missing = EXPECTED_MODELS - registered
    assert not missing, f"Missing mappers: {sorted(missing)}"


def test_configure_mappers_succeeds_after_load_all_models() -> None:
    load_all_models()

    configure_mappers()


def test_user_portfolio_relationship_resolves_after_load_all_models() -> None:
    load_all_models()

    user_mapper = class_mapper(User)
    portfolio_mapper = class_mapper(Portfolio)

    assert "portfolios" in user_mapper.relationships
    assert "user" in portfolio_mapper.relationships
