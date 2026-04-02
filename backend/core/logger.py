"""
core/logger.py
──────────────
Structured JSON logger used across all backend modules.
Every log entry is a JSON object — easy to ship to Azure Monitor or any log aggregator.

Usage:
    from core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Document uploaded", extra={"document_id": doc_id, "user_id": user_id})
"""
import logging
import json
import sys
from datetime import datetime, timezone

from core.config import settings


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any `extra` dict fields passed by the caller
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            ):
                log_obj[key] = value

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger with JSON formatting."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    level = logging.DEBUG if settings.APP_ENV == "development" else logging.INFO
    logger.setLevel(level)
    logger.propagate = False

    return logger
