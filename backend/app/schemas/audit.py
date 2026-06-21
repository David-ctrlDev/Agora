from datetime import datetime

from pydantic import BaseModel


class AuditRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int | None
    action: str
    summary: str
    actor_name: str | None
    created_at: datetime
