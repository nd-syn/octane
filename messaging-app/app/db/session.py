"""Async SQLAlchemy engine and session factory.

Sets SQLite PRAGMAs (WAL mode, busy timeout) on every connection via an
event listener. WAL mode allows concurrent readers + one writer, which is
exactly what we need for a small messaging app on aiosqlite.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _register_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Apply PRAGMAs to every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_engine() -> AsyncEngine:
    """Create and cache the global engine. Idempotent."""
    global _engine, _sessionmaker
    if _engine is not None:
        return _engine

    settings = get_settings()
    connect_args: dict[str, Any] = {}
    if _is_sqlite(settings.database_url):
        connect_args["check_same_thread"] = False

    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )

    if _is_sqlite(settings.database_url):
        # aiosqlite uses the sync DBAPI under the hood; this listener still fires.
        event.listen(_engine.sync_engine, "connect", _register_sqlite_pragmas)

    _sessionmaker = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        autoflush=False,
    )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Yields a session, commits on success, rolls back on error."""
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Called on app shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
