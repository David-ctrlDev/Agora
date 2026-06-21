from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GoogleStatus(BaseModel):
    connected: bool
    scopes: str | None = None


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
