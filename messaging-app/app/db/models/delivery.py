"""Per-recipient delivery row. Read state lives here."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.user import User


class MessageDelivery(Base):
    __tablename__ = "message_deliveries"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    delivered_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=utcnow_iso
    )
    read_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    message: Mapped["Message"] = relationship(back_populates="deliveries")
    user: Mapped["User"] = relationship(lazy="joined")

    __table_args__ = (
        # Partial index: only rows where read_at IS NULL. Speeds up unread
        # counts. SQLite supports partial indexes via the `postgresql_where`
        # workaround — use `dialect_condition` or just a regular index here
        # and accept the small cost. We use a plain index for portability.
        Index("idx_deliveries_user_unread", user_id, message_id),
    )
