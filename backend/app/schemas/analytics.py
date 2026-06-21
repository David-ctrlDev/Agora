from datetime import date

from pydantic import BaseModel


class ProjectAnalytics(BaseModel):
    project_id: int
    name: str
    status: str
    total: int
    done: int
    open: int
    blocked: int
    overdue: int
    completion_pct: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    health: str
    due_date: date | None = None
    due_in_days: int | None = None
    area_name: str | None = None
    category: str | None = None
    criticality: str | None = None
    project_type: str | None = None
    initiative: str | None = None
    process: str | None = None


class OverviewTotals(BaseModel):
    projects: int
    active_projects: int
    total_tasks: int
    done_tasks: int
    completion_pct: int
    overdue_tasks: int
    at_risk_projects: int


class AreaStat(BaseModel):
    area: str
    projects: int
    completion_pct: int
    at_risk: int


class Overview(BaseModel):
    projects: list[ProjectAnalytics]
    totals: OverviewTotals
    by_area: list[AreaStat] = []
    task_by_status: dict[str, int] = {}
    project_by_status: dict[str, int] = {}
    by_criticality: dict[str, int] = {}
