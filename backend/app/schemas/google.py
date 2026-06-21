from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoogleStatus(BaseModel):
    connected: bool
    scopes: str | None = None


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    attendees: list[str] = []
    when: str | None = None  # ISO 8601 opcional


class MeetingResult(BaseModel):
    title: str
    meet_url: str | None = None
    web_url: str
    starts_at: datetime


class GoogleDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    source: str
    external_id: str
    title: str
    kind: str | None
    web_url: str | None
    occurred_at: datetime | None
