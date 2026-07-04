from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.schemas.follow import FollowListResponse, FollowResponse, FollowUser
from app.schemas.user import UserResponse
from app.services.follow import FollowService

router = APIRouter()


@router.post("/{user_id}", response_model=FollowResponse, status_code=201)
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = FollowService(session)
    follow = await svc.follow(current_user, user_id)
    return FollowResponse(status=follow.status)


@router.delete("/{user_id}", status_code=204)
async def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = FollowService(session)
    await svc.unfollow(current_user, user_id)


@router.get("/followers", response_model=FollowListResponse)
async def get_followers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = FollowService(session)
    users, total = await svc.get_followers(current_user, limit=limit, offset=offset)
    return FollowListResponse(
        users=[FollowUser(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            bio=u.bio,
            avatar_url=u.avatar_url,
            followed_at="",
        ) for u in users],
        total=total,
    )


@router.get("/following", response_model=FollowListResponse)
async def get_following(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = FollowService(session)
    users, total = await svc.get_following(current_user, limit=limit, offset=offset)
    return FollowListResponse(
        users=[FollowUser(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            bio=u.bio,
            avatar_url=u.avatar_url,
            followed_at="",
        ) for u in users],
        total=total,
    )
