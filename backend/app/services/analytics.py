"""Métricas de avance por proyecto y resumen global, filtradas por área."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.models.project import Project
from app.models.project_progress_snapshot import ProjectProgressSnapshot
from app.models.task import Task
from app.models.user import User
from app.schemas.analytics import (
    AreaStat,
    Overview,
    OverviewTotals,
    ProjectAnalytics,
    QuarterCategoryStat,
    QuarterlyTracking,
)
from app.services import projects as projects_svc

_STATUSES = ["todo", "in_progress", "blocked", "approval", "done"]
_PRIORITIES = ["high", "medium", "low"]


def _health(total: int, done: int, overdue: int, blocked: int) -> str:
    if total == 0:
        return "sin_tareas"
    if done == total:
        return "completado"
    if overdue > 0:
        return "en_riesgo"
    if blocked > 0:
        return "atencion"
    return "en_curso"


def _metrics(project: Project, tasks: list[Task], today: date) -> ProjectAnalytics:
    by_status = {s: 0 for s in _STATUSES}
    by_priority = {p: 0 for p in _PRIORITIES}
    overdue = 0
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1
        by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
        if task.due_date is not None and task.due_date < today and task.status != "done":
            overdue += 1
    total = len(tasks)
    done = by_status["done"]
    blocked = by_status["blocked"]
    return ProjectAnalytics(
        project_id=project.id,
        name=project.name,
        status=project.status,
        total=total,
        done=done,
        open=total - done,
        blocked=blocked,
        overdue=overdue,
        completion_pct=round(done / total * 100) if total else 0,
        by_status=by_status,
        by_priority=by_priority,
        health=_health(total, done, overdue, blocked),
        due_date=project.due_date,
        due_in_days=(project.due_date - today).days if project.due_date else None,
        category=project.category,
        criticality=project.criticality,
        project_type=project.project_type,
        initiative=project.initiative,
        process=project.process,
    )


async def project_metrics(db: AsyncSession, project: Project) -> ProjectAnalytics:
    tasks = list(
        (
            await db.execute(
                select(Task).where(
                    Task.project_id == project.id, Task.is_adjustment.is_(False)
                )
            )
        ).scalars().all()
    )
    metrics = _metrics(project, tasks, date.today())
    adj = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(Task.status != "done"),
            ).where(Task.project_id == project.id, Task.is_adjustment.is_(True))
        )
    ).one()
    metrics.adjustments_total = int(adj[0] or 0)
    metrics.adjustments_open = int(adj[1] or 0)
    return metrics


async def overview(db: AsyncSession, user: User) -> Overview:
    project_ids = await projects_svc.accessible_project_ids(db, user)
    if not project_ids:
        return Overview(
            projects=[],
            totals=OverviewTotals(
                projects=0,
                active_projects=0,
                total_tasks=0,
                done_tasks=0,
                completion_pct=0,
                overdue_tasks=0,
                at_risk_projects=0,
            ),
        )
    projects = list(
        (await db.execute(select(Project).where(Project.id.in_(project_ids)))).scalars().all()
    )
    tasks = list(
        (
            await db.execute(
                select(Task).where(
                    Task.project_id.in_(project_ids), Task.is_adjustment.is_(False)
                )
            )
        ).scalars().all()
    )
    today = date.today()
    grouped: dict[int, list[Task]] = {p.id: [] for p in projects}
    for task in tasks:
        grouped.setdefault(task.project_id, []).append(task)
    items = [_metrics(p, grouped.get(p.id, []), today) for p in projects]
    # Proyectos en riesgo primero, luego por nombre.
    items.sort(key=lambda m: (m.health != "en_riesgo", m.name.lower()))

    total_tasks = sum(m.total for m in items)
    done_tasks = sum(m.done for m in items)

    # Ajustes (post-entrega): agregado global y por proyecto, aparte del avance.
    adj_rows = (
        await db.execute(
            select(
                Task.project_id,
                func.count(),
                func.count().filter(Task.status != "done"),
            )
            .where(Task.project_id.in_(project_ids), Task.is_adjustment.is_(True))
            .group_by(Task.project_id)
        )
    ).all()
    adj_by_project = {pid: (int(t or 0), int(o or 0)) for pid, t, o in adj_rows}
    for m in items:
        m.adjustments_total, m.adjustments_open = adj_by_project.get(m.project_id, (0, 0))
    adjustments_total = sum(t for t, _ in adj_by_project.values())
    adjustments_open = sum(o for _, o in adj_by_project.values())

    totals = OverviewTotals(
        projects=len(items),
        active_projects=sum(1 for p in projects if p.status == "active"),
        total_tasks=total_tasks,
        done_tasks=done_tasks,
        completion_pct=round(done_tasks / total_tasks * 100) if total_tasks else 0,
        overdue_tasks=sum(m.overdue for m in items),
        at_risk_projects=sum(1 for m in items if m.health == "en_riesgo"),
        adjustments_total=adjustments_total,
        adjustments_open=adjustments_open,
        adjustments_done=adjustments_total - adjustments_open,
    )

    # --- Agregados para el dashboard ---
    area_rows = (
        await db.execute(select(Area.id, Area.name).where(Area.id.in_([p.area_id for p in projects])))
    ).all()
    area_name = {aid: name for aid, name in area_rows}
    item_by_id = {m.project_id: m for m in items}

    area_agg: dict[int, dict[str, int]] = {}
    for p in projects:
        m = item_by_id[p.id]
        m.area_name = area_name.get(p.area_id)
        agg = area_agg.setdefault(p.area_id, {"projects": 0, "done": 0, "total": 0, "at_risk": 0})
        agg["projects"] += 1
        agg["done"] += m.done
        agg["total"] += m.total
        if m.health == "en_riesgo":
            agg["at_risk"] += 1
    by_area = sorted(
        (
            AreaStat(
                area=area_name.get(aid, "—"),
                projects=agg["projects"],
                completion_pct=round(agg["done"] / agg["total"] * 100) if agg["total"] else 0,
                at_risk=agg["at_risk"],
            )
            for aid, agg in area_agg.items()
        ),
        key=lambda a: -a.projects,
    )

    task_by_status = {s: 0 for s in _STATUSES}
    for m in items:
        for s, count in m.by_status.items():
            task_by_status[s] = task_by_status.get(s, 0) + count

    project_by_status: dict[str, int] = {}
    by_criticality: dict[str, int] = {}
    for p in projects:
        project_by_status[p.status] = project_by_status.get(p.status, 0) + 1
        crit = (p.criticality or "").strip().upper() or "Sin definir"
        by_criticality[crit] = by_criticality.get(crit, 0) + 1

    return Overview(
        projects=items,
        totals=totals,
        by_area=by_area,
        task_by_status=task_by_status,
        project_by_status=project_by_status,
        by_criticality=by_criticality,
    )


# --- Seguimiento trimestral ------------------------------------------------


def _quarter_bounds(year: int, quarter: int) -> tuple[date, date]:
    start_month = 3 * (quarter - 1) + 1
    start = date(year, start_month, 1)
    if quarter == 4:
        end = date(year, 12, 31)
    else:
        end = date(year, start_month + 3, 1) - timedelta(days=1)
    return start, end


async def quarterly_tracking(
    db: AsyncSession, user: User, *, year: int, quarter: int
) -> QuarterlyTracking:
    """Proyectos "trabajados" en un trimestre: aquellos cuyo rango [inicio, entrega]
    se cruza con el trimestre. Un proyecto que dura varios trimestres aparece en cada
    uno. El % es el **cumplimiento del plan**: avance real a la fecha de referencia
    (hoy si el trimestre está en curso; el cierre si es pasado) dividido por el avance
    esperado según el cronograma lineal a esa fecha, topado en 100%. Un proyecto justo
    al día marca 100%. Segmentado por área."""
    quarter = min(max(quarter, 1), 4)
    q_start, q_end = _quarter_bounds(year, quarter)
    today = date.today()
    is_current = q_start <= today <= q_end
    label = f"TRIMESTRE {quarter} DE {year}"

    project_ids = await projects_svc.accessible_project_ids(db, user)
    if not project_ids:
        return QuarterlyTracking(
            year=year, quarter=quarter, label=label, start=q_start, end=q_end,
            total_projects=0, avg_progress=0, is_current=is_current,
            without_dates=0, by_category=[], min_year=None, max_year=None,
        )

    rows = (
        await db.execute(
            select(
                Project.id, Project.category, Project.progress,
                Project.start_date, Project.due_date,
            ).where(Project.id.in_(project_ids))
        )
    ).all()

    # Fecha de referencia: hoy si el trimestre está en curso/futuro, el cierre si es pasado.
    ref = min(q_end, today)

    starts: list[date] = []
    ends: list[date] = []
    without_dates = 0
    members: list[tuple[int, str | None, date, date]] = []  # (id, categoría, inicio, fin)
    current: dict[int, int] = {}  # avance actual por proyecto
    for pid, category, progress, sd, dd in rows:
        eff_start = sd or dd
        eff_end = dd or sd
        if eff_start is None:  # sin ninguna fecha -> no ubicable en trimestres
            without_dates += 1
            continue
        starts.append(eff_start)
        ends.append(eff_end)
        if eff_start <= q_end and eff_end >= q_start:  # el rango cruza el trimestre
            members.append((pid, category, eff_start, eff_end))
            current[pid] = progress

    min_year = min(d.year for d in starts) if starts else None
    max_year = max(d.year for d in ends) if ends else None

    # Avance real a la fecha de referencia. Trimestre en curso/futuro: avance actual.
    # Pasado: último snapshot con fecha <= cierre; si no hay, cae al avance actual.
    actual: dict[int, int] = dict(current)
    member_ids = [pid for pid, _, _, _ in members]
    if member_ids and q_end < today:
        snaps = (
            await db.execute(
                select(ProjectProgressSnapshot.project_id, ProjectProgressSnapshot.progress)
                .where(
                    ProjectProgressSnapshot.project_id.in_(member_ids),
                    func.date(ProjectProgressSnapshot.captured_at) <= q_end,
                )
                .order_by(
                    ProjectProgressSnapshot.project_id, ProjectProgressSnapshot.captured_at
                )
            )
        ).all()
        for pid, prog in snaps:  # orden ascendente -> gana el más reciente <= cierre
            actual[pid] = prog

    def fulfillment(pid: int, s: date, d: date) -> int:
        """Cumplimiento = avance real / avance esperado (cronograma lineal a `ref`), tope 100."""
        if d <= s:  # proyecto puntual: se espera terminado en/tras su fecha
            expected = 100.0 if ref >= s else 0.0
        else:
            frac = (min(ref, d) - s).days / (d - s).days
            expected = max(0.0, min(1.0, frac)) * 100.0
        if expected <= 0:  # aún no debía empezar -> nada pendiente
            return 100
        return min(100, round(actual[pid] / expected * 100))

    scores = [(category, fulfillment(pid, s, d)) for pid, category, s, d in members]
    total = len(scores)
    avg = round(sum(sc for _, sc in scores) / total) if total else 0

    by_cat: dict[str, list[int]] = {}
    for category, sc in scores:
        cat = (category or "").strip().upper() or "SIN CATEGORÍA"
        by_cat.setdefault(cat, []).append(sc)
    by_category = [
        QuarterCategoryStat(category=c, count=len(v), avg_progress=round(sum(v) / len(v)))
        for c, v in by_cat.items()
    ]
    by_category.sort(key=lambda stat: (-stat.count, stat.category))

    return QuarterlyTracking(
        year=year, quarter=quarter, label=label, start=q_start, end=q_end,
        total_projects=total, avg_progress=avg, is_current=is_current,
        without_dates=without_dates, by_category=by_category,
        min_year=min_year, max_year=max_year,
    )
