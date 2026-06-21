from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SprintStatus = Literal["planned", "active", "completed"]


class SprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str | None = None
    start_date: date
    end_date: date
    status: SprintStatus = "planned"


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: SprintStatus | None = None


class SprintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    goal: str | None
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    total: int = 0
    done: int = 0
    completion_pct: int = 0


class BurndownPoint(BaseModel):
    date: date
    ideal: float
    remaining: int | None = None


class Burndown(BaseModel):
    sprint_id: int
    total: int
    points: list[BurndownPoint]
