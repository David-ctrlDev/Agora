from datetime import datetime

from pydantic import BaseModel, Field


class AreaCatalogItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    member_count: int = 0
    leads: list[str] = []
    is_member: bool = False
    pending: bool = False  # ya tiene una solicitud de unión pendiente


class NewAreaRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class AreaRequestRead(BaseModel):
    id: int
    kind: str  # join | new_area
    status: str  # pending | approved | rejected
    area_id: int | None = None
    area_name: str | None = None
    proposed_name: str | None = None
    proposed_description: str | None = None
    requester_id: int
    requester_name: str | None = None
    requester_email: str | None = None
    note: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


class DecisionPayload(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
