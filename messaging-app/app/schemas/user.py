from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    created_at: str

    model_config = {"from_attributes": True}


class UserSearchResponse(BaseModel):
    users: list[UserResponse]
    total: int


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(None, max_length=64)
    bio: str | None = Field(None, max_length=500)
    avatar_url: str | None = Field(None, max_length=512)
