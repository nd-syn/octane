"""User model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.conversation import ConversationMember
    from app.db.models.follow import Follow


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    is_active: Mapped[int] = mapped_column(default=1, nullable=False)

    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow_iso)
    updated_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=utcnow_iso, onupdate=utcnow_iso
    )

    # ORM relationships
    memberships: Mapped[list["ConversationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    outgoing_follows: Mapped[list["Follow"]] = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    incoming_follows: Mapped[list["Follow"]] = relationship(
        "Follow",
        foreign_keys="Follow.followee_id",
        back_populates="followee",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_users_username_lower", func.lower(username)),
        Index("idx_users_email_lower", func.lower(email)),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"
