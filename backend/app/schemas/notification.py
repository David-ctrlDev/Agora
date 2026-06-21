from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str
    severity: str
    status: str
    area_id: int | None
    project_id: int | None
    created_at: datetime
