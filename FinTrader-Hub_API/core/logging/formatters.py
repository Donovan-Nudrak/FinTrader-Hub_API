import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

SENSITIVE_PATTERNS = (
    re.compile(r"(password|passwd|secret|token|api[_-]?key|authorization)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
)


def _redact_message(message: str) -> str:
    redacted = message
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact_message(record.msg)
        if record.args:
            record.args = tuple(
                _redact_message(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_message(record.getMessage()),
        }
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "task_name",
            "task_duration_ms",
            "alert_id",
            "asset_id",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
