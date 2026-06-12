import logging
import sys

from core.config import Settings
from core.logging.formatters import JsonFormatter, SensitiveDataFilter


def setup_logging(settings: Settings) -> None:
    log_level_name = settings.resolved_log_level
    log_level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.addFilter(SensitiveDataFilter())

    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
