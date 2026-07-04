"""Structured logging with structlog.

NEVER log message plaintext, message ciphertext, conversation keys, the master
key, passwords, full JWTs, or refresh tokens. Log IDs only.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# Per-request/connection ID, set by middleware. Empty in background tasks.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def _add_request_id(_logger: Any, _method: str, event_dict: dict) -> dict:
    event_dict.setdefault("request_id", request_id_var.get())
    return event_dict


def configure_logging(env: str) -> None:
    """Configure structlog + stdlib logging once at startup."""
    is_prod = env == "prod"

    # stdlib root logger — capture uvicorn and other libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_request_id,
            (
                structlog.processors.JSONRenderer()
                if is_prod
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.INFO if is_prod else logging.DEBUG
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
