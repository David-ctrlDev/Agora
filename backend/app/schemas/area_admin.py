from pydantic import BaseModel

from app.schemas.admin import ActivityProject, ActivityTask


class AreaLite(BaseModel):
    id: int
    name: str
    slug: str


class AreaAdminScope(BaseModel):
    areas: list[AreaLite]


class AreaAdminStats(BaseModel):
    areas: int
    projects: int
    active_projects: int
    tasks: int
    open_tasks: int
    overdue_tasks: int
    members: int


class AreaAdminActivity(BaseModel):
    recent_projects: list[ActivityProject]
    recent_tasks: list[ActivityTask]


class AreaMemberRow(BaseModel):
    user_id: int
    name: str
    email: str
    area_id: int
    area_name: str
    area_role: str


class AreaAdminMembers(BaseModel):
    members: list[AreaMemberRow]


class AreaMemberSet(BaseModel):
    user_id: int
    area_role: str = "member"  # member | lead
