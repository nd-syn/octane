from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.follows import router as follows_router
from app.api.conversations import router as conversations_router
from app.api.messages import router as messages_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(follows_router, prefix="/follows", tags=["follows"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(messages_router, prefix="/conversations", tags=["messages"])

__all__ = ["api_router"]
