import logging
import time

from infrastructure.database.session import SessionLocal
from infrastructure.tasks.celery_app import celery_app
from modules.market.services import MarketService

logger = logging.getLogger(__name__)


def _run_task(task_name: str, handler) -> dict[str, int]:
    start = time.perf_counter()
    db = SessionLocal()
    try:
        logger.info("Celery task started", extra={"task_name": task_name})
        result = handler(db)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Celery task completed",
            extra={"task_name": task_name, "task_duration_ms": duration_ms, "result": result},
        )
        return result
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "Celery task failed",
            extra={"task_name": task_name, "task_duration_ms": duration_ms},
            exc_info=exc,
        )
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="health.ping")
def health_ping() -> str:
    return "pong"


@celery_app.task(name="market.update_market_prices")
def update_market_prices() -> dict[str, int]:
    def handler(db):
        service = MarketService(db)
        return service.update_market_prices()

    return _run_task("market.update_market_prices", handler)


@celery_app.task(name="market.update_news_feed")
def update_news_feed() -> dict[str, int]:
    def handler(db):
        service = MarketService(db)
        return service.update_news_feed()

    return _run_task("market.update_news_feed", handler)
