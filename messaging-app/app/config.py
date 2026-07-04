"""Application configuration loaded from environment variables.

Single source of truth. In production, the app refuses to start if secrets
are missing or too short. In dev, missing values get safe placeholders so
local development never blocks on key generation.
"""

from __future__ import annotations

import base64
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime config. See .env.example for documentation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: str = "dev"  # "dev" | "prod"

    # Database
    database_url: str = "sqlite+aiosqlite:///./messaging.db"

    # Secrets (base64-encoded). Validated on access via the validator below.
    jwt_secret: str = ""
    master_key: str = ""

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Token lifetimes, in seconds
    access_token_ttl: int = 900  # 15 min
    refresh_token_ttl: int = 2_592_000  # 30 days

    # Optional S3 backup target
    backup_s3_url: str = ""

    @field_validator("env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"dev", "prod"}:
            raise ValueError("ENV must be 'dev' or 'prod'")
        return v

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def get_jwt_secret(self) -> bytes:
        """Decode and validate the JWT secret. Fail fast in prod."""
        secret = self.jwt_secret
        if not secret:
            if self.is_prod:
                raise RuntimeError("JWT_SECRET is required in production")
            return b"dev-only-jwt-secret-do-not-use-in-prod-32b!!"
        try:
            decoded = base64.b64decode(secret, validate=True)
        except Exception as e:
            raise RuntimeError(f"JWT_SECRET is not valid base64: {e}") from e
        if len(decoded) < 32:
            if self.is_prod:
                raise RuntimeError(
                    f"JWT_SECRET must decode to at least 32 bytes (got {len(decoded)})"
                )
            # pad short dev secrets so the rest of the code can assume >= 32
            return decoded.ljust(32, b"!")
        return decoded

    def get_master_key(self) -> bytes:
        """Decode and validate the master key. Fail fast in prod."""
        key = self.master_key
        if not key:
            if self.is_prod:
                raise RuntimeError("MASTER_KEY is required in production")
            # Deterministic 32-byte dev key so SQLite files are portable
            # between local dev machines. NEVER use this in prod.
            return b"\x00" * 32
        try:
            decoded = base64.b64decode(key, validate=True)
        except Exception as e:
            raise RuntimeError(f"MASTER_KEY is not valid base64: {e}") from e
        if len(decoded) != 32:
            raise RuntimeError(
                f"MASTER_KEY must decode to exactly 32 bytes (got {len(decoded)})"
            )
        return decoded


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Validated at first access."""
    return Settings()
