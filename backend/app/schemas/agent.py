from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_type: str
    params: dict[str, Any]
    status: str
    result: dict[str, Any] | None
    created_at: datetime


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mime_type: str | None = None
    source: str
    char_count: int
    created_at: datetime


class DriveAttachCreate(BaseModel):
    file_id: str = Field(min_length=1)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[int] = Field(default_factory=list)


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    action: ActionRead | None = None
