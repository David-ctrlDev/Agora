"""Servicios de administración (solo admin global)."""
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.models.area import Area
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.user_area import UserArea
from app.schemas.admin import (
    ActivityProject,
    ActivityTask,
    ActivityUser,
    AdminActivity,
    AdminAreaMembership,
    AdminStats,
    AdminUserCreate,
    AdminUserRead,
    AdminUserUpdate,
    AreaAssignment,
)


async def system_stats(db: AsyncSession) -> AdminStats:
    async def count(model, *where) -> int:
        stmt = select(func.count()).select_from(model)
        if where:
            stmt = stmt.where(*where)
        return int((await db.execute(stmt)).scalar() or 0)

    return AdminStats(
        users=await count(User),
        active_users=await count(User, User.is_active.is_(True)),
        admins=await count(User, User.role == "admin"),
        two_fa=await count(User, User.totp_enabled.is_(True)),
        areas=await count(Area),
        projects=await count(Project),
        active_projects=await count(Project, Project.status == "active"),
        tasks=await count(Task),
        open_tasks=await count(Task, Task.status != "done"),
        overdue_tasks=await count(
            Task,
            Task.status != "done",
            Task.due_date.is_not(None),
            Task.due_date < func.current_date(),
        ),
        google_provider=settings.google_provider,
        gemini_provider=settings.gemini_provider,
    )


async def recent_activity(db: AsyncSession, *, limit: int = 10) -> AdminActivity:
    """Feeds de auditoría para el panel admin: últimos proyectos y tareas creadas,
    últimos ingresos y últimos usuarios registrados. Solo admin (ve todas las áreas)."""
    owner = aliased(User)
    proj_rows = (
        await db.execute(
            select(
                Project.id,
                Project.name,
                Project.status,
                Project.created_at,
                Area.name,
                owner.name,
            )
            .join(Area, Area.id == Project.area_id)
            .outerjoin(owner, owner.id == Project.owner_id)
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
    ).all()
    recent_projects = [
        ActivityProject(
            id=pid, name=name, status=st, created_at=created, area_name=area, owner_name=own
        )
        for pid, name, st, created, area, own in proj_rows
    ]

    assignee = aliased(User)
    task_rows = (
        await db.execute(
            select(
                Task.id,
                Task.title,
                Task.status,
                Task.priority,
                Task.project_id,
                Task.created_at,
                Project.name,
                assignee.name,
            )
            .join(Project, Project.id == Task.project_id)
            .outerjoin(assignee, assignee.id == Task.assignee_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
    ).all()
    recent_tasks = [
        ActivityTask(
            id=tid,
            title=title,
            status=st,
            priority=prio,
            project_id=proj_id,
            created_at=created,
            project_name=proj_name,
            assignee_name=assignee_name,
        )
        for tid, title, st, prio, proj_id, created, proj_name, assignee_name in task_rows
    ]

    login_rows = (
        await db.execute(
            select(User.id, User.name, User.email, User.role, User.last_login_at)
            .where(User.last_login_at.is_not(None))
            .order_by(User.last_login_at.desc())
            .limit(limit)
        )
    ).all()
    recent_logins = [
        ActivityUser(id=uid, name=name, email=email, role=role, at=at)
        for uid, name, email, role, at in login_rows
    ]

    user_rows = (
        await db.execute(
            select(User.id, User.name, User.email, User.role, User.created_at)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
    ).all()
    recent_users = [
        ActivityUser(id=uid, name=name, email=email, role=role, at=at)
        for uid, name, email, role, at in user_rows
    ]

    return AdminActivity(
        recent_projects=recent_projects,
        recent_tasks=recent_tasks,
        recent_logins=recent_logins,
        recent_users=recent_users,
    )

_ROLES = {"admin", "member"}
_AREA_ROLES = {"lead", "member"}


class EmailExists(Exception):
    pass


async def _areas_by_user(db: AsyncSession) -> dict[int, list[AdminAreaMembership]]:
    rows = (
        await db.execute(
            select(UserArea.user_id, UserArea.area_id, UserArea.area_role, Area.name).join(
                Area, Area.id == UserArea.area_id
            )
        )
    ).all()
    out: dict[int, list[AdminAreaMembership]] = {}
    for uid, area_id, area_role, name in rows:
        out.setdefault(uid, []).append(
            AdminAreaMembership(area_id=area_id, name=name, area_role=area_role)
        )
    return out


def _to_read(user: User, areas: list[AdminAreaMembership]) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        twofa_enabled=user.totp_enabled,
        areas=areas,
    )


async def list_users(db: AsyncSession) -> list[AdminUserRead]:
    users = (await db.execute(select(User).order_by(User.role, User.name))).scalars().all()
    by_user = await _areas_by_user(db)
    return [_to_read(u, by_user.get(u.id, [])) for u in users]


async def _read_one(db: AsyncSession, user: User) -> AdminUserRead:
    by_user = await _areas_by_user(db)
    return _to_read(user, by_user.get(user.id, []))


async def create_user(db: AsyncSession, payload: AdminUserCreate) -> AdminUserRead:
    email = payload.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise EmailExists()
    role = payload.role if payload.role in _ROLES else "member"
    user = User(
        email=email,
        name=payload.name.strip(),
        role=role,
        is_active=True,
        default_area_id=payload.area_ids[0] if payload.area_ids else None,
    )
    db.add(user)
    await db.flush()
    for area_id in payload.area_ids:
        db.add(UserArea(user_id=user.id, area_id=area_id, area_role="member"))
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)


async def update_user(db: AsyncSession, user: User, payload: AdminUserUpdate) -> AdminUserRead:
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.email is not None:
        email = payload.email.strip().lower()
        if email != user.email:
            taken = (
                await db.execute(select(User).where(User.email == email, User.id != user.id))
            ).scalar_one_or_none()
            if taken is not None:
                raise EmailExists()
            user.email = email
    if payload.role in _ROLES:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)


async def reset_2fa(db: AsyncSession, user: User) -> AdminUserRead:
    """Desactiva y borra el 2FA de un usuario (p. ej. perdió su dispositivo)."""
    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)


async def set_user_areas(
    db: AsyncSession, user: User, areas: list[AreaAssignment]
) -> AdminUserRead:
    await db.execute(delete(UserArea).where(UserArea.user_id == user.id))
    for a in areas:
        role = a.area_role if a.area_role in _AREA_ROLES else "member"
        db.add(UserArea(user_id=user.id, area_id=a.area_id, area_role=role))
    if areas and user.default_area_id is None:
        user.default_area_id = areas[0].area_id
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)
