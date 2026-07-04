"""FastAPI application entrypoint.

Wires the lifespan (engine init + dispose), configures logging, mounts
routers, CORS, and exception handlers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import api_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.db.session import dispose_engine, get_sessionmaker, init_engine
from app.logging_config import configure_logging, get_logger
from app.ws import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Init engine, validate config, dispose on shutdown."""
    settings = get_settings()

    _ = settings.get_jwt_secret()
    _ = settings.get_master_key()

    configure_logging(settings.env)
    log = get_logger("app.startup")
    log.info(
        "starting",
        env=settings.env,
        database_url=_redact_db_url(settings.database_url),
    )

    init_engine()

    try:
        sm = get_sessionmaker()
        async with sm() as s:
            await s.execute(text("SELECT 1"))
        log.info("db_ok")
    except Exception as e:
        log.warning("db_unreachable_at_startup", error=str(e))

    yield

    await dispose_engine()
    log.info("shutdown_complete")


def _redact_db_url(url: str) -> str:
    """Strip any credentials from the URL for logging."""
    if "@" in url:
        scheme, rest = url.split("://", 1)
        _, host = rest.split("@", 1)
        return f"{scheme}://***@{host}"
    return url


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Octane",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "detail": exc.message},
        )

    @app.get("/health")
    async def health() -> dict:
        try:
            sm = get_sessionmaker()
            async with sm() as s:
                await s.execute(text("SELECT 1"))
            return {"status": "ok", "db": "ok"}
        except Exception as e:
            return {"status": "degraded", "db": "error", "detail": str(e)}

    app.include_router(api_router)
    app.include_router(ws_router, prefix="/ws")

    return app


app = create_app()
