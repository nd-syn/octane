"""Message model — stores ciphertext only; server decrypts on delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._helpers import utcnow_iso

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.message import MessageDelivery
    from app.db.models.user import User


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # nacl.secretbox output: 24-byte nonce + ciphertext + 16-byte tag
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow_iso)
    edited_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    conversation: Mapped["Conversation"] = relationship(lazy="joined")
    sender: Mapped["User"] = relationship(lazy="joined")
    deliveries: Mapped[list["MessageDelivery"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_messages_conv_time", conversation_id, created_at),
        Index("idx_messages_sender", sender_id),
    )
