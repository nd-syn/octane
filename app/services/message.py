from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.crypto import (
    unwrap_conversation_key,
    encrypt_message,
    decrypt_message,
    b64e,
    b64d,
)
from app.db.models import (
    Conversation,
    ConversationMember,
    Message,
    MessageDelivery,
    User,
)
from app.core.exceptions import (
    ConversationNotFound,
    MessageNotFound,
    NotAMember,
    NotMutualFollow,
)


class MessageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def send_message(
        self, conversation_id: int, sender: User, content: str, reply_to_id: int | None = None
    ) -> Message:
        conv_result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.members))
        )
        conv = conv_result.scalar_one_or_none()
        if not conv:
            raise ConversationNotFound("conversation not found")

        is_member = any(m.user_id == sender.id for m in conv.members)
        if not is_member:
            raise NotAMember("you are not a member of this conversation")

        if reply_to_id:
            reply_msg = await self.session.get(Message, reply_to_id)
            if not reply_msg or reply_msg.conversation_id != conversation_id:
                reply_to_id = None

        master_key = self.settings.get_master_key()
        conv_key = unwrap_conversation_key(master_key, conv.encrypted_key)
        plaintext = content.encode("utf-8")
        ciphertext = encrypt_message(conv_key, plaintext)

        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender.id,
            ciphertext=ciphertext,
            reply_to_id=reply_to_id,
        )
        self.session.add(msg)
        await self.session.flush()

        conv.last_message_id = msg.id
        conv.updated_at = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        )

        for member in conv.members:
            delivery = MessageDelivery(
                message_id=msg.id,
                user_id=member.user_id,
            )
            self.session.add(delivery)

        if sender.id in [m.user_id for m in conv.members]:
            sender_delivery = await self.session.get(
                MessageDelivery, (msg.id, sender.id)
            )
            if sender_delivery:
                sender_delivery.read_at = (
                    datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                )

        await self.session.flush()
        return msg

    async def get_messages(
        self,
        conversation_id: int,
        user: User,
        limit: int = 50,
        offset: int = 0,
        before_id: int | None = None,
    ) -> tuple[list[Message], int]:
        conv_result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = conv_result.scalar_one_or_none()
        if not conv:
            raise ConversationNotFound("conversation not found")

        is_member = await self.session.get(
            ConversationMember, (conversation_id, user.id)
        )
        if not is_member:
            raise NotAMember("you are not a member of this conversation")

        count_stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .options(selectinload(Message.sender))
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages, total

    async def delete_message(
        self, conversation_id: int, message_id: int, user: User
    ) -> None:
        conv = await self.session.get(Conversation, conversation_id)
        if not conv:
            raise ConversationNotFound("conversation not found")

        msg = await self.session.get(Message, message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise MessageNotFound("message not found")

        if msg.sender_id != user.id:
            raise NotAMember("cannot delete another user's message")

        msg.deleted_at = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        )
        await self.session.flush()

    async def mark_read(self, conversation_id: int, message_id: int, user: User) -> None:
        member = await self.session.get(
            ConversationMember, (conversation_id, user.id)
        )
        if not member:
            raise NotAMember("you are not a member of this conversation")

        delivery = await self.session.get(MessageDelivery, (message_id, user.id))
        if delivery and not delivery.read_at:
            delivery.read_at = (
                datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            )

        if not member.last_read_message_id or message_id > member.last_read_message_id:
            member.last_read_message_id = message_id

    async def decrypt_message_content(self, conv: Conversation, msg: Message) -> str:
        if msg.deleted_at:
            return ""
        master_key = self.settings.get_master_key()
        conv_key = unwrap_conversation_key(master_key, conv.encrypted_key)
        plaintext = decrypt_message(conv_key, msg.ciphertext)
        return plaintext.decode("utf-8")
