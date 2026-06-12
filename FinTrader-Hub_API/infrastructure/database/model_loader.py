"""Central ORM model registration for all application entrypoints."""

from sqlalchemy.orm import configure_mappers

from infrastructure.database.base import Base


def load_all_models() -> None:
    """Import every SQLAlchemy model package so mapper relationships resolve.

    Must run before any ORM operation outside FastAPI router imports
    (Celery workers, Alembic, scripts).
    """
    import modules.alerts.models  # noqa: F401
    import modules.asset.models  # noqa: F401
    import modules.auth.models  # noqa: F401
    import modules.market.models  # noqa: F401
    import modules.portfolio.models  # noqa: F401
    import modules.settings.models  # noqa: F401
    import modules.trade.models  # noqa: F401

    configure_mappers()


def get_registered_model_names() -> set[str]:
    return {mapper.class_.__name__ for mapper in Base.registry.mappers}
