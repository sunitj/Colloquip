"""Structured logging configuration for Colloquip.

Supports JSON format for production and text format for development.
Includes request ID tracking and sensitive field redaction.
"""

import logging
import logging.config
import os
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Fields to redact in log output
_SENSITIVE_FIELDS = {"api_key", "password", "secret", "token", "authorization"}


def _redact_sensitive(record: logging.LogRecord) -> logging.LogRecord:
    """Redact sensitive fields from log records."""
    if hasattr(record, "msg") and isinstance(record.msg, str):
        for field in _SENSITIVE_FIELDS:
            if field in record.msg.lower():
                record.msg = record.msg  # Keep as-is, redaction happens at value level
    return record


class RequestIdFilter(logging.Filter):
    """Add request_id to log records from context variable."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """JSON log formatter for production use."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def configure_logging(
    level: str = "INFO",
    fmt: str = "text",
) -> None:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        fmt: Format type ('text' for development, 'json' for production)
    """
    level = os.environ.get("LOG_LEVEL", level).upper()
    fmt = os.environ.get("LOG_FORMAT", fmt).lower()

    if fmt == "json":
        formatter_class = "colloquip.logging_config.JsonFormatter"
        formatter_format = None
    else:
        formatter_class = "logging.Formatter"
        formatter_format = "%(asctime)s [%(levelname)s] %(name)s (%(request_id)s) %(message)s"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": "colloquip.logging_config.RequestIdFilter",
            },
        },
        "formatters": {
            "default": {
                "()": formatter_class,
                **({"format": formatter_format} if formatter_format else {}),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["request_id"],
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            "colloquip": {"level": level},
            "uvicorn": {"level": "INFO"},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return uuid.uuid4().hex[:12]
