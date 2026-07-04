from pydantic import BaseModel


class ParticipantUser(BaseModel):
    id: int
    username: str
    display_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    type: str
    title: str | None
    participants: list[ParticipantUser]
    last_message: str | None
    last_message_at: str | None
    unread_count: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CreateConversationRequest(BaseModel):
    user_id: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
