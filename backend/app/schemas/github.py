import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_FULL_NAME_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


class GitHubRepoCreate(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def _validate(cls, value: str) -> str:
        value = value.strip()
        if not _FULL_NAME_RE.match(value):
            raise ValueError("Formato esperado: owner/repo")
        return value


class GitHubRepoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    full_name: str
    html_url: str | None
    created_at: datetime


class GitHubEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: int
    event_type: str
    title: str
    author: str | None
    html_url: str | None
    occurred_at: datetime
