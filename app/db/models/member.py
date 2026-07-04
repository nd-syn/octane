"""ConversationMember model — join table with per-user state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.user import User


class ConversationMember(Base):
    __tablename__ = "conversation_members"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow_iso)
    last_read_message_id: Mapped[int | None] = mapped_column(nullable=True)
    is_muted: Mapped[int] = mapped_column(default=0, nullable=False)

    conversation: Mapped["Conversation"] = relationship(
        back_populates="members", lazy="joined"
    )
    user: Mapped["User"] = relationship(back_populates="memberships", lazy="joined")

    __table_args__ = (
        # Composite PK on (conversation_id, user_id). We add a separate
        # index on user_id for the "list my conversations" query.
        Index("idx_members_user", user_id),
    )
