"""Refresh token model. Stores SHA-256 of the token, not the token itself."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.user import User


def _new_family() -> str:
    return uuid.uuid4().hex


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(32), nullable=False, default=_new_family)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow_iso)
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(lazy="joined")

    __table_args__ = (
        Index("idx_refresh_tokens_user", user_id),
        Index("idx_refresh_tokens_family", family_id),
    )
