from typing import Any

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    hash: str
    short: str
    author: str
    date: str
    message: str
    files: list[str] = []


class BranchInfo(BaseModel):
    name: str
    is_default: bool
    last: dict[str, Any] | None = None
    ahead: int = 0


class CodeStatus(BaseModel):
    initialized: bool
    default_branch: str
    branches: list[BranchInfo]


class ChangedFile(BaseModel):
    status: str
    path: str


class RestoreRequest(BaseModel):
    hash: str = Field(min_length=4, max_length=64)
    branch: str = "main"


class GitignoreCategory(BaseModel):
    id: str
    title: str
    description: str
    patterns: list[str]
    recommended: bool = False


class GitignoreState(BaseModel):
    content: str
    active: list[str]
    extra: str
    categories: list[GitignoreCategory]


class GitignoreUpdate(BaseModel):
    categories: list[str] = []
    extra: str = ""


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class DiffResult(BaseModel):
    files: list[ChangedFile]
    diffs: dict[str, str]
    binary: list[str] = []


class MergeRequest(BaseModel):
    branch: str
    message: str | None = None
    # ruta -> 'draft' (borrador) | 'main' (línea oficial)
    resolutions: dict[str, str] | None = None


class MergeConflictsOut(BaseModel):
    conflicts: list[str]
