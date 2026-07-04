"""Shared helpers for SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow_iso() -> str:
    """ISO-8601 UTC, second precision. Stable, sortable, round-trips Pydantic."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
