from pydantic import BaseModel


class AreaMembership(BaseModel):
    id: int
    name: str
    slug: str
    area_role: str


class CurrentUser(BaseModel):
    id: int
    email: str
    name: str
    role: str
    avatar_url: str | None
    areas: list[AreaMembership]


class DevUser(BaseModel):
    id: int
    email: str
    name: str
    role: str
    areas: list[str]


class DevLoginRequest(BaseModel):
    user_id: int
