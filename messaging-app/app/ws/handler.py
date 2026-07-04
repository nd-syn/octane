"""WebSocket handler for real-time messaging.

Clients connect to /ws?token=<access_token>.
Once connected, they can send and receive messages in real time.

Protocol:
  Client -> Server (JSON):
    {"type": "message", "conversation_id": 1, "content": "hello", "reply_to_id": null}
    {"type": "typing", "conversation_id": 1}
    {"type": "read", "conversation_id": 1, "message_id": 42}

  Server -> Client (JSON):
    {"type": "new_message", "message": {...}}
    {"type": "typing", "conversation_id": 1, "user_id": 2, "username": "alice"}
    {"type": "read", "conversation_id": 1, "user_id": 2, "message_id": 42}
    {"type": "error", "detail": "..."}
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_token
from app.db.models import User, ConversationMember
from app.core.exceptions import AppError
from app.db.session import get_session
from app.services.message import MessageService
from app.services.conversation import ConversationService

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                c for c in self._connections[user_id] if c != ws
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def send_to_user(self, user_id: int, data: dict[str, Any]) -> None:
        if user_id in self._connections:
            for ws in self._connections[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass

    async def broadcast_to_conversation(
        self, conversation_id: int, data: dict[str, Any], session: AsyncSession
    ) -> None:
        result = await session.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id
            )
        )
        member_ids = [row[0] for row in result.all()]
        for uid in member_ids:
            await self.send_to_user(uid, data)


manager = ConnectionManager()


async def _get_user_from_token(token: str, session: AsyncSession) -> User | None:
    try:
        settings = get_settings()
        secret = settings.get_jwt_secret()
        payload = decode_token(token, secret)
        user_id = int(payload["sub"])
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.websocket("")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    session_gen = get_session()
    session = await session_gen.__anext__()

    try:
        query_params = dict(ws.query_params)
        token = query_params.get("token", token)
        if not token:
            await ws.close(code=4001, reason="missing token")
            return

        user = await _get_user_from_token(token, session)
        if not user:
            await ws.close(code=4001, reason="invalid token")
            return

        await manager.connect(user.id, ws)

        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "invalid JSON"})
                continue

            msg_type = data.get("type")
            if msg_type == "message":
                conv_id = data.get("conversation_id")
                content = data.get("content", "")
                if not conv_id or not content:
                    await ws.send_json({"type": "error", "detail": "missing conversation_id or content"})
                    continue

                is_member = await session.get(ConversationMember, (conv_id, user.id))
                if not is_member:
                    await ws.send_json({"type": "error", "detail": "not a member"})
                    continue

                msg_svc = MessageService(session)
                conv_svc = ConversationService(session)
                msg = await msg_svc.send_message(conv_id, user, content, data.get("reply_to_id"))
                conv = await conv_svc.get_conversation(conv_id, user)
                plaintext = await msg_svc.decrypt_message_content(conv, msg)

                payload = {
                    "type": "new_message",
                    "message": {
                        "id": msg.id,
                        "conversation_id": msg.conversation_id,
                        "sender_id": user.id,
                        "sender_username": user.username,
                        "content": plaintext,
                        "reply_to_id": msg.reply_to_id,
                        "created_at": msg.created_at,
                    },
                }
                await manager.broadcast_to_conversation(conv_id, payload, session)

            elif msg_type == "typing":
                conv_id = data.get("conversation_id")
                if conv_id:
                    payload = {
                        "type": "typing",
                        "conversation_id": conv_id,
                        "user_id": user.id,
                        "username": user.username,
                    }
                    await manager.broadcast_to_conversation(conv_id, payload, session)

            elif msg_type == "read":
                conv_id = data.get("conversation_id")
                message_id = data.get("message_id")
                if conv_id and message_id:
                    msg_svc = MessageService(session)
                    await msg_svc.mark_read(conv_id, message_id, user)
                    payload = {
                        "type": "read",
                        "conversation_id": conv_id,
                        "user_id": user.id,
                        "message_id": message_id,
                    }
                    await manager.broadcast_to_conversation(conv_id, payload, session)

            else:
                await ws.send_json({"type": "error", "detail": f"unknown type: {msg_type}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
    finally:
        if user:
            manager.disconnect(user.id, ws)
        try:
            await session_gen.__anext__()
        except StopAsyncIteration:
            pass
