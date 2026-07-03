from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["todo", "in_progress", "blocked", "done"]
TaskPriority = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    assignee_id: int | None = None
    due_date: date | None = None
    sprint_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    sprint_id: int | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    status: str
    priority: str
    assignee_id: int | None
    due_date: date | None
    sprint_id: int | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    assignee_name: str | None = None
    project_name: str | None = None


class TaskSummaryItem(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_date: date | None
    assignee_id: int | None
    assignee_name: str | None
    project_id: int
    project_name: str
    area_name: str
    overdue: bool


class TaskGroupStat(BaseModel):
    key: str
    count: int
    open: int
    overdue: int


class TaskSummary(BaseModel):
    total: int
    open: int
    done: int
    overdue: int
    unassigned: int
    by_assignee: list[TaskGroupStat]
    by_area: list[TaskGroupStat]
    by_status: dict[str, int]
    items: list[TaskSummaryItem]
