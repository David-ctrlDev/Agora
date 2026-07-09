from datetime import datetime

from pydantic import BaseModel, Field


class AdminAreaMembership(BaseModel):
    area_id: int
    name: str
    area_role: str


class AdminUserRead(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    twofa_enabled: bool
    can_view_costs: bool = False
    areas: list[AdminAreaMembership]


class AdminUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    role: str = "member"  # admin | member
    area_ids: list[int] = []


class AdminUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    role: str | None = None  # admin | member
    is_active: bool | None = None
    can_view_costs: bool | None = None


class AreaAssignment(BaseModel):
    area_id: int
    area_role: str = "member"  # lead | member


class UserAreasSet(BaseModel):
    areas: list[AreaAssignment] = []


class AdminAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class AdminStats(BaseModel):
    users: int
    active_users: int
    admins: int
    two_fa: int
    areas: int
    projects: int
    active_projects: int
    tasks: int
    open_tasks: int
    overdue_tasks: int
    google_provider: str
    gemini_provider: str


class ActivityProject(BaseModel):
    id: int
    name: str
    status: str
    area_name: str | None = None
    owner_name: str | None = None
    created_at: datetime


class ActivityTask(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    project_id: int
    project_name: str | None = None
    assignee_name: str | None = None
    created_at: datetime


class ActivityUser(BaseModel):
    id: int
    name: str
    email: str
    role: str
    at: datetime  # último ingreso (recent_logins) o alta (recent_users)


class AdminActivity(BaseModel):
    recent_projects: list[ActivityProject]
    recent_tasks: list[ActivityTask]
    recent_logins: list[ActivityUser]
    recent_users: list[ActivityUser]
