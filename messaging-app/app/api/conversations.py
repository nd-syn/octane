from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.schemas.conversation import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    ParticipantUser,
)
from app.services.conversation import ConversationService
from app.services.follow import FollowService

router = APIRouter()


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conv_svc = ConversationService(session)
    conversations, total = await conv_svc.list_conversations(
        current_user, limit=limit, offset=offset
    )

    items = []
    for conv in conversations:
        participants = [
            ParticipantUser(
                id=m.user.id,
                username=m.user.username,
                display_name=m.user.display_name,
                avatar_url=m.user.avatar_url,
            )
            for m in conv.members
        ]
        unread = await conv_svc.get_unread_count(conv.id, current_user.id)
        last_msg = await conv_svc.get_last_message(conv.id)
        items.append(ConversationResponse(
            id=conv.id,
            type=conv.type,
            title=conv.title,
            participants=participants,
            last_message="",
            last_message_at=last_msg.created_at if last_msg else None,
            unread_count=unread,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        ))

    return ConversationListResponse(conversations=items, total=total)


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conv_svc = ConversationService(session)
    conv = await conv_svc.get_or_create_direct(current_user, body.user_id)

    participants = [
        ParticipantUser(
            id=m.user.id,
            username=m.user.username,
            display_name=m.user.display_name,
            avatar_url=m.user.avatar_url,
        )
        for m in conv.members
    ]
    return ConversationResponse(
        id=conv.id,
        type=conv.type,
        title=conv.title,
        participants=participants,
        last_message=None,
        last_message_at=None,
        unread_count=0,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conv_svc = ConversationService(session)
    conv = await conv_svc.get_conversation(conversation_id, current_user)

    participants = [
        ParticipantUser(
            id=m.user.id,
            username=m.user.username,
            display_name=m.user.display_name,
            avatar_url=m.user.avatar_url,
        )
        for m in conv.members
    ]
    unread = await conv_svc.get_unread_count(conv.id, current_user.id)
    return ConversationResponse(
        id=conv.id,
        type=conv.type,
        title=conv.title,
        participants=participants,
        last_message=None,
        last_message_at=None,
        unread_count=unread,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )
