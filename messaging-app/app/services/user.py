from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.core.exceptions import UserNotFound


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFound("user not found")
        return user

    async def get_by_username(self, username: str) -> User:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFound(f"user '{username}' not found")
        return user

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> tuple[list[User], int]:
        stmt = select(User).where(
            or_(
                User.username.ilike(f"%{query}%"),
                User.display_name.ilike(f"%{query}%"),
            )
        ).order_by(User.username)

        count_stmt = select(User.id).where(
            or_(
                User.username.ilike(f"%{query}%"),
                User.display_name.ilike(f"%{query}%"),
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = len(total_result.all())

        result = await self.session.execute(stmt.offset(offset).limit(limit))
        users = list(result.scalars().all())
        return users, total

    async def update_profile(
        self,
        user: User,
        display_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        if display_name is not None:
            user.display_name = display_name
        if bio is not None:
            user.bio = bio
        if avatar_url is not None:
            user.avatar_url = avatar_url
        await self.session.flush()
        return user
