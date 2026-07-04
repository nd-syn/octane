"""Conversation model — unified for direct + group."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.conversation import ConversationMember
    from app.db.models.message import Message


VALID_TYPES = ("direct", "group")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="direct")
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Wrapped per-conversation key (24 nonce + 32 ct + 16 tag = 72 bytes)
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow_iso)
    updated_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=utcnow_iso, onupdate=utcnow_iso
    )
    last_message_id: Mapped[int | None] = mapped_column(
        nullable=True
    )  # FK to messages, added in message model

    members: Mapped[list["ConversationMember"]] = relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('direct','group')",
            name="ck_conversations_type",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversation id={self.id} type={self.type}>"
