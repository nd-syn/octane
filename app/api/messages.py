from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.schemas.message import MessageResponse, SendMessageRequest, SenderInfo
from app.services.message import MessageService
from app.services.conversation import ConversationService

router = APIRouter()


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg_svc = MessageService(session)
    conv_svc = ConversationService(session)
    conv = await conv_svc.get_conversation(conversation_id, current_user)
    messages, total = await msg_svc.get_messages(
        conversation_id, current_user, limit=limit, offset=offset
    )

    items = []
    for msg in messages:
        content = await msg_svc.decrypt_message_content(conv, msg)
        items.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender=SenderInfo(
                id=msg.sender.id,
                username=msg.sender.username,
                display_name=msg.sender.display_name,
            ),
            content=content,
            reply_to_id=msg.reply_to_id,
            created_at=msg.created_at,
            edited_at=msg.edited_at,
            deleted_at=msg.deleted_at,
        ))
    return items


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg_svc = MessageService(session)
    conv_svc = ConversationService(session)
    conv = await conv_svc.get_conversation(conversation_id, current_user)
    msg = await msg_svc.send_message(
        conversation_id, current_user, body.content, body.reply_to_id
    )
    content = await msg_svc.decrypt_message_content(conv, msg)
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender=SenderInfo(
            id=msg.sender.id,
            username=msg.sender.username,
            display_name=msg.sender.display_name,
        ),
        content=content,
        reply_to_id=msg.reply_to_id,
        created_at=msg.created_at,
        edited_at=msg.edited_at,
        deleted_at=msg.deleted_at,
    )


@router.delete("/{conversation_id}/messages/{message_id}", status_code=204)
async def delete_message(
    conversation_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg_svc = MessageService(session)
    await msg_svc.delete_message(conversation_id, message_id, current_user)


@router.put("/{conversation_id}/messages/{message_id}/read", status_code=204)
async def mark_read(
    conversation_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg_svc = MessageService(session)
    await msg_svc.mark_read(conversation_id, message_id, current_user)
