from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.schemas.user import (
    UpdateProfileRequest,
    UserResponse,
    UserSearchResponse,
)
from app.services.user import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = UserService(session)
    user = await svc.update_profile(
        user=current_user,
        display_name=body.display_name,
        bio=body.bio,
        avatar_url=body.avatar_url,
    )
    return UserResponse.model_validate(user)


@router.get("/search", response_model=UserSearchResponse)
async def search_users(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    svc = UserService(session)
    users, total = await svc.search(query=q, limit=limit, offset=offset)
    return UserSearchResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
    )


@router.get("/{username}", response_model=UserResponse)
async def get_user(
    username: str,
    session: AsyncSession = Depends(get_session),
):
    svc = UserService(session)
    user = await svc.get_by_username(username)
    return UserResponse.model_validate(user)
