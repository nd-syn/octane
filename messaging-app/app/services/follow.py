from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Follow, User
from app.core.exceptions import CannotMessageSelf, UserNotFound


class FollowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def follow(self, follower: User, followee_id: int) -> Follow:
        if follower.id == followee_id:
            raise CannotMessageSelf("cannot follow yourself")

        followee = await self.session.get(User, followee_id)
        if not followee:
            raise UserNotFound("user not found")

        existing = await self.session.get(Follow, (follower.id, followee_id))
        if existing:
            if existing.status == "blocked":
                raise CannotMessageSelf("cannot follow this user")
            existing.status = "accepted"
            await self.session.flush()
            return existing

        follow = Follow(follower_id=follower.id, followee_id=followee_id, status="accepted")
        self.session.add(follow)
        await self.session.flush()
        return follow

    async def unfollow(self, follower: User, followee_id: int) -> None:
        existing = await self.session.get(Follow, (follower.id, followee_id))
        if existing:
            await self.session.delete(existing)
            await self.session.flush()

    async def get_followers(
        self, user: User, limit: int = 50, offset: int = 0
    ) -> tuple[list[User], int]:
        stmt = (
            select(User)
            .join(Follow, Follow.follower_id == User.id)
            .where(
                Follow.followee_id == user.id,
                Follow.status == "accepted",
            )
            .order_by(Follow.created_at.desc())
        )
        count_stmt = (
            select(User.id)
            .join(Follow, Follow.follower_id == User.id)
            .where(
                Follow.followee_id == user.id,
                Follow.status == "accepted",
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = len(total_result.all())

        result = await self.session.execute(stmt.offset(offset).limit(limit))
        users = list(result.scalars().all())
        return users, total

    async def get_following(
        self, user: User, limit: int = 50, offset: int = 0
    ) -> tuple[list[User], int]:
        stmt = (
            select(User)
            .join(Follow, Follow.followee_id == User.id)
            .where(
                Follow.follower_id == user.id,
                Follow.status == "accepted",
            )
            .order_by(Follow.created_at.desc())
        )
        count_stmt = (
            select(User.id)
            .join(Follow, Follow.followee_id == User.id)
            .where(
                Follow.follower_id == user.id,
                Follow.status == "accepted",
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = len(total_result.all())

        result = await self.session.execute(stmt.offset(offset).limit(limit))
        users = list(result.scalars().all())
        return users, total

    async def is_following(self, follower_id: int, followee_id: int) -> bool:
        follow = await self.session.get(Follow, (follower_id, followee_id))
        return follow is not None and follow.status == "accepted"
