from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["planned", "active", "on_hold", "done", "archived"]
MemberRole = Literal["owner", "editor", "viewer"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    area_id: int
    status: ProjectStatus = "planned"
    start_date: date | None = None
    due_date: date | None = None
    progress: int = Field(default=0, ge=0, le=100)
    category: str | None = None
    process: str | None = None
    project_type: str | None = None


class RoadmapFields(BaseModel):
    initiative: str | None = None
    proposed_by: str | None = None
    project_type: str | None = None
    category: str | None = None
    criticality: str | None = None
    process: str | None = None
    benefits: str | None = None
    change_management: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    due_date: date | None = None
    owner_id: int | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    initiative: str | None = None
    proposed_by: str | None = None
    project_type: str | None = None
    category: str | None = None
    criticality: str | None = None
    process: str | None = None
    benefits: str | None = None
    change_management: str | None = None


class ProjectRead(RoadmapFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    area_id: int
    status: str
    owner_id: int | None
    start_date: date | None
    due_date: date | None
    progress: int
    created_at: datetime
    updated_at: datetime
    area_name: str | None = None
    owner_name: str | None = None
    is_mine: bool = False  # el usuario actual es dueño o miembro del proyecto


class ProjectMemberRead(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class ProjectMemberCreate(BaseModel):
    user_id: int
    role: MemberRole = "editor"
