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
    # Ajustes (post-entrega): métricas aparte, no cuentan en el avance.
    adjustments_total: int = 0
    adjustments_open: int = 0
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
    adjustments_total: int = 0
    adjustments_open: int = 0
    adjustments_done: int = 0


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


class QuarterCategoryStat(BaseModel):
    category: str
    count: int
    avg_progress: int


class QuarterlyTracking(BaseModel):
    year: int
    quarter: int  # 1..4
    label: str
    start: date
    end: date
    total_projects: int  # proyectos trabajados (con rango que cruza el trimestre)
    avg_progress: int  # % de avance al cierre del trimestre (histórico) o actual
    is_current: bool  # el trimestre en curso (usa avance actual, no snapshot)
    without_dates: int  # proyectos accesibles sin fechas (no ubicables en trimestres)
    by_category: list[QuarterCategoryStat] = []
    min_year: int | None = None
    max_year: int | None = None
