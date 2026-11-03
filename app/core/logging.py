"""
Structured JSON logging configuration for RouteWise.

Provides:
* ``configure_logging(debug)`` – call once at startup.
* ``get_logger(name)`` – return a stdlib logger with structured output.
* ``RequestIDFilter`` – inject ``request_id`` into every log record.
"""

from __future__ import annotations

import json as _json
import logging
import sys
from contextvars import ContextVar
from typing import Any

# Context variable holding the current request ID (set per-request).
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    """Store *request_id* for the current async context."""
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    """Retrieve the current request ID (or ``"-"``)."""
    return _request_id_ctx.get()


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class RequestIDFilter(logging.Filter):
    """Attach ``request_id`` from the current context to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()  # type: ignore[attr-defined]
        return True


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data  # type: ignore[attr-defined]
        return _json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def configure_logging(debug: bool = False) -> None:
    """Set up the root logger with structured JSON output.

    Call once during application startup (e.g., in ``main.py``).
    """
    level = logging.DEBUG if debug else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    # Remove pre-existing handlers to avoid duplicate output on reload.
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(_JSONFormatter())
    console.addFilter(RequestIDFilter())

    root.addHandler(console)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that inherits the root JSON configuration."""
    logger = logging.getLogger(name)
    # Ensure the request-id filter is present even if configure_logging
    # hasn't been called yet (e.g. during import-time usage).
    if not any(isinstance(f, RequestIDFilter) for f in logger.filters):
        logger.addFilter(RequestIDFilter())
    return logger
