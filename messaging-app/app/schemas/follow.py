from pydantic import BaseModel


class FollowRequest(BaseModel):
    user_id: int


class FollowUser(BaseModel):
    id: int
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    followed_at: str

    model_config = {"from_attributes": True}


class FollowResponse(BaseModel):
    status: str


class FollowListResponse(BaseModel):
    users: list[FollowUser]
    total: int
