"""Sprints y burndown. La autorización por área se aplica en el router."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sprint import Sprint
from app.models.task import Task
from app.schemas.sprint import Burndown, BurndownPoint, SprintCreate, SprintRead, SprintUpdate

_MAX_DAYS = 120


def _to_read(sprint: Sprint, total: int = 0, done: int = 0) -> SprintRead:
    return SprintRead(
        id=sprint.id,
        project_id=sprint.project_id,
        name=sprint.name,
        goal=sprint.goal,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        status=sprint.status,
        created_at=sprint.created_at,
        total=total,
        done=done,
        completion_pct=round(done / total * 100) if total else 0,
    )


async def _counts(db: AsyncSession, sprint_id: int) -> tuple[int, int]:
    row = (
        await db.execute(
            select(
                func.count(Task.id),
                func.count(Task.id).filter(Task.status == "done"),
            ).where(Task.sprint_id == sprint_id)
        )
    ).one()
    return int(row[0]), int(row[1])


async def list_sprints(db: AsyncSession, project_id: int) -> list[SprintRead]:
    sprints = list(
        (
            await db.execute(
                select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.start_date)
            )
        ).scalars().all()
    )
    if not sprints:
        return []
    rows = (
        await db.execute(
            select(
                Task.sprint_id,
                func.count(Task.id),
                func.count(Task.id).filter(Task.status == "done"),
            )
            .where(Task.sprint_id.in_([s.id for s in sprints]))
            .group_by(Task.sprint_id)
        )
    ).all()
    counts = {sid: (int(total), int(done)) for sid, total, done in rows}
    return [_to_read(s, *counts.get(s.id, (0, 0))) for s in sprints]


async def get_sprint(db: AsyncSession, sprint_id: int) -> Sprint | None:
    return await db.get(Sprint, sprint_id)


async def create_sprint(db: AsyncSession, project_id: int, payload: SprintCreate) -> SprintRead:
    sprint = Sprint(
        project_id=project_id,
        name=payload.name.strip(),
        goal=payload.goal or None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
    )
    db.add(sprint)
    await db.commit()
    await db.refresh(sprint)
    return _to_read(sprint)


async def update_sprint(db: AsyncSession, sprint: Sprint, payload: SprintUpdate) -> SprintRead:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sprint, key, value)
    await db.commit()
    await db.refresh(sprint)
    total, done = await _counts(db, sprint.id)
    return _to_read(sprint, total, done)


async def delete_sprint(db: AsyncSession, sprint: Sprint) -> None:
    await db.delete(sprint)
    await db.commit()


async def burndown(db: AsyncSession, sprint: Sprint) -> Burndown:
    tasks = list(
        (await db.execute(select(Task).where(Task.sprint_id == sprint.id))).scalars().all()
    )
    total = len(tasks)
    start = sprint.start_date
    end = sprint.end_date if sprint.end_date >= sprint.start_date else sprint.start_date
    span = min((end - start).days, _MAX_DAYS)
    days = [start + timedelta(days=i) for i in range(span + 1)]
    n = len(days)
    today = date.today()
    completed = sorted(t.completed_at.date() for t in tasks if t.completed_at is not None)
    points: list[BurndownPoint] = []
    for i, day in enumerate(days):
        ideal = total * (1 - i / (n - 1)) if n > 1 else 0.0
        remaining = None
        if day <= today:
            remaining = total - sum(1 for cd in completed if cd <= day)
        points.append(BurndownPoint(date=day, ideal=round(ideal, 1), remaining=remaining))
    return Burndown(sprint_id=sprint.id, total=total, points=points)
