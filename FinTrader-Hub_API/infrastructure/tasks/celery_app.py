from celery import Celery

from core.config import get_settings
from infrastructure.database.model_loader import load_all_models

load_all_models()

settings = get_settings()

celery_app = Celery(
    "fintraderhub",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "infrastructure.tasks.market_tasks",
        "infrastructure.tasks.alert_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "update-market-prices": {
            "task": "market.update_market_prices",
            "schedule": settings.market_price_update_minutes * 60.0,
        },
        "update-news-feed": {
            "task": "market.update_news_feed",
            "schedule": settings.news_feed_update_minutes * 60.0,
        },
        "evaluate-alerts": {
            "task": "alerts.evaluate_alerts",
            "schedule": 300.0,
        },
    },
)
