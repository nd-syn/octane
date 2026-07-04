from sqlalchemy import or_, select, func, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.crypto import (
    generate_conversation_key,
    wrap_conversation_key,
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
    CannotMessageSelf,
    ConversationNotFound,
    NotAMember,
    NotMutualFollow,
    UserNotFound,
)


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_or_create_direct(
        self, creator: User, other_user_id: int
    ) -> Conversation:
        if creator.id == other_user_id:
            raise CannotMessageSelf("cannot create conversation with yourself")

        other = await self.session.get(User, other_user_id)
        if not other:
            raise UserNotFound("user not found")

        existing = await self._find_direct_conversation(creator.id, other_user_id)
        if existing:
            return existing

        master_key = self.settings.get_master_key()
        conv_key = generate_conversation_key()
        wrapped = wrap_conversation_key(master_key, conv_key)

        conv = Conversation(type="direct", encrypted_key=wrapped)
        self.session.add(conv)
        await self.session.flush()

        self.session.add(ConversationMember(conversation_id=conv.id, user_id=creator.id))
        self.session.add(ConversationMember(conversation_id=conv.id, user_id=other_user_id))
        await self.session.flush()

        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conv.id)
            .options(selectinload(Conversation.members).selectinload(ConversationMember.user))
        )
        return result.scalar_one()

    async def list_conversations(
        self, user: User, limit: int = 50, offset: int = 0
    ) -> tuple[list[Conversation], int]:
        subq = (
            select(ConversationMember.conversation_id)
            .where(ConversationMember.user_id == user.id)
            .subquery()
        )

        count_stmt = select(func.count()).select_from(subq)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(Conversation)
            .where(Conversation.id.in_(select(subq.c.conversation_id)))
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user),
            )
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        conversations = list(result.scalars().all())
        return conversations, total

    async def get_conversation(self, conversation_id: int, user: User) -> Conversation:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user),
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise ConversationNotFound("conversation not found")

        is_member = any(m.user_id == user.id for m in conv.members)
        if not is_member:
            raise NotAMember("you are not a member of this conversation")

        return conv

    async def get_unread_count(self, conversation_id: int, user_id: int) -> int:
        member = await self.session.get(
            ConversationMember, (conversation_id, user_id)
        )
        if not member or not member.last_read_message_id:
            stmt = select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id,
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.id > member.last_read_message_id,
            Message.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_last_message(self, conversation_id: int) -> Message | None:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_direct_conversation(
        self, user1_id: int, user2_id: int
    ) -> Conversation | None:
        c1 = (
            select(ConversationMember.conversation_id)
            .where(ConversationMember.user_id == user1_id)
            .subquery()
        )
        c2 = (
            select(ConversationMember.conversation_id)
            .where(ConversationMember.user_id == user2_id)
            .subquery()
        )
        stmt = (
            select(Conversation)
            .where(
                Conversation.id.in_(select(c1.c.conversation_id)),
                Conversation.id.in_(select(c2.c.conversation_id)),
                Conversation.type == "direct",
            )
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
