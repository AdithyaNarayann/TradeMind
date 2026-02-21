"""Structured logging setup for the FastAPI backend."""
from __future__ import annotations

import logging
import os
import structlog
from datetime import datetime, timezone
from typing import Optional


_DEFAULT_LEVEL = "INFO"
_CONFIGURED = False
_HANDLER_NAME = "structured_console"


class _Iso8601Formatter(logging.Formatter):
    """Formatter that emits ISO 8601 timestamps in UTC."""

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return timestamp.isoformat()


def _parse_level(raw_level: str) -> int:
    level = (raw_level or _DEFAULT_LEVEL).strip().upper()
    return logging.getLevelName(level) if isinstance(logging.getLevelName(level), int) else logging.INFO


def setup_logging() -> None:
    """
    Configure structured logging for console output.

    Safe to call multiple times; only configures once.
    """
    global _CONFIGURED

    root_logger = logging.getLogger()

    if _CONFIGURED or any(getattr(h, "name", "") == _HANDLER_NAME for h in root_logger.handlers):
        return

    level = _parse_level(os.getenv("LOG_LEVEL", _DEFAULT_LEVEL))

    handler = logging.StreamHandler()
    handler.name = _HANDLER_NAME
    handler.setLevel(level)

    formatter = _Iso8601Formatter(
        fmt="ts=%(asctime)s level=%(levelname)s module=%(module)s msg=%(message)s",
    )
    handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    logging.captureWarnings(True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(level)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


# Usage example (in main.py):
# from app.core.logging import setup_logging
# setup_logging()
