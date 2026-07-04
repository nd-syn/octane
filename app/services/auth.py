from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.crypto import b64d, random_token
from app.core.security import (
    decode_token,
    encode_access_token,
    encode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.core.exceptions import (
    EmailTaken,
    InvalidCredentials,
    TokenExpired,
    TokenInvalid,
    UsernameTaken,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def signup(
        self, username: str, email: str, password: str, display_name: str | None = None
    ) -> tuple[User, str, str]:
        existing_user = await self.session.execute(
            select(User).where(
                (User.username == username) | (User.email == email)
            )
        )
        existing = existing_user.scalar_one_or_none()
        if existing:
            if existing.username == username:
                raise UsernameTaken(f"username '{username}' is taken")
            raise EmailTaken(f"email '{email}' is taken")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            display_name=display_name or username,
        )
        self.session.add(user)
        await self.session.flush()

        access_token, refresh_token = await self._generate_tokens(user)
        return user, access_token, refresh_token

    async def login(self, username: str, password: str) -> tuple[User, str, str]:
        result = await self.session.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentials("invalid username or password")

        access_token, refresh_token = await self._generate_tokens(user)
        return user, access_token, refresh_token

    async def refresh(self, refresh_token_str: str) -> tuple[User, str, str]:
        secret = self.settings.get_jwt_secret()
        try:
            payload = decode_token(refresh_token_str, secret)
        except TokenExpired:
            raise TokenExpired("refresh token expired")
        except TokenInvalid:
            raise TokenInvalid("invalid refresh token")

        token_hash = hash_refresh_token(refresh_token_str)
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()
        if not stored:
            raise TokenInvalid("refresh token revoked or not found")

        user_result = await self.session.execute(
            select(User).where(User.id == int(payload["sub"]))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise TokenInvalid("user not found")

        stored.revoked_at = datetime.now(timezone.utc).isoformat()
        await self.session.flush()

        access_token, new_refresh_token = await self._generate_tokens(user)
        return user, access_token, new_refresh_token

    async def logout(self, refresh_token_str: str) -> None:
        token_hash = hash_refresh_token(refresh_token_str)
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()
        if stored:
            stored.revoked_at = datetime.now(timezone.utc).isoformat()
            await self.session.flush()

    async def _generate_tokens(self, user: User) -> tuple[str, str]:
        secret = self.settings.get_jwt_secret()
        access_token = encode_access_token(
            user_id=user.id,
            secret=secret,
            ttl_seconds=self.settings.access_token_ttl,
        )

        jwt_token, plain_token = encode_refresh_token(
            user_id=user.id,
            secret=secret,
            ttl_seconds=self.settings.refresh_token_ttl,
        )

        expires_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )

        rt = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(jwt_token),
            expires_at=expires_at,
        )
        self.session.add(rt)
        await self.session.flush()

        return access_token, jwt_token
