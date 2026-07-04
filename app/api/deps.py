from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_session
from app.core.exceptions import TokenInvalid, TokenExpired


async def get_current_user(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization.startswith("Bearer "):
        raise TokenInvalid("invalid authorization header")
    token = authorization[7:]

    settings = get_settings()
    secret = settings.get_jwt_secret()
    try:
        payload = decode_token(token, secret)
    except TokenExpired:
        raise TokenExpired("access token expired")
    except TokenInvalid:
        raise TokenInvalid("invalid access token")

    user_id = int(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise TokenInvalid("user not found")
    return user
