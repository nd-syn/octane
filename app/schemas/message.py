from pydantic import BaseModel, Field


class SenderInfo(BaseModel):
    id: int
    username: str
    display_name: str | None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender: SenderInfo
    content: str
    reply_to_id: int | None
    created_at: str
    edited_at: str | None
    deleted_at: str | None
    delivery_status: str = "sent"

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    reply_to_id: int | None = None
