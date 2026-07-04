"""Follow (asymmetric) model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.user import User


VALID_STATUSES = ("accepted", "pending", "blocked")


class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    followee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="accepted")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow_iso)

    follower: Mapped["User"] = relationship(
        "User", foreign_keys=[follower_id], back_populates="outgoing_follows"
    )
    followee: Mapped["User"] = relationship(
        "User", foreign_keys=[followee_id], back_populates="incoming_follows"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('accepted','pending','blocked')",
            name="ck_follows_status",
        ),
        Index("idx_follows_followee_status", followee_id, status),
        Index("idx_follows_follower_status", follower_id, status),
    )
