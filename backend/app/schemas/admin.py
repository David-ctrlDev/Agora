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
    areas: list[AdminAreaMembership]


class AdminUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    role: str = "member"  # admin | member
    area_ids: list[int] = []


class AdminUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = None  # admin | member
    is_active: bool | None = None


class AreaAssignment(BaseModel):
    area_id: int
    area_role: str = "member"  # lead | member


class UserAreasSet(BaseModel):
    areas: list[AreaAssignment] = []


class AdminAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None
