import logging
import time

from infrastructure.database.session import SessionLocal
from infrastructure.tasks.celery_app import celery_app
from modules.alerts.services import AlertService

logger = logging.getLogger(__name__)


@celery_app.task(name="alerts.evaluate_alerts")
def evaluate_alerts() -> dict[str, int]:
    task_name = "alerts.evaluate_alerts"
    start = time.perf_counter()
    db = SessionLocal()
    try:
        logger.info("Celery task started", extra={"task_name": task_name})
        service = AlertService(db)
        result = service.evaluate_all_active_alerts()
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Alert evaluation completed",
            extra={"task_name": task_name, "task_duration_ms": duration_ms, "result": result},
        )
        return result
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "Alert evaluation task failed",
            extra={"task_name": task_name, "task_duration_ms": duration_ms},
            exc_info=exc,
        )
        db.rollback()
        raise
    finally:
        db.close()
