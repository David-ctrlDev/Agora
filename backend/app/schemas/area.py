from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
