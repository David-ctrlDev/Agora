"""Panel del administrador de área: datos y acciones acotados a las áreas que
administra (rol de área lead/admin). El super admin ve todas las áreas."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.deps import admin_area_ids
from app.models.area import Area
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.user_area import UserArea
from app.schemas.admin import ActivityProject, ActivityTask
from app.schemas.area_admin import (
    AreaAdminActivity,
    AreaAdminMembers,
    AreaAdminScope,
    AreaAdminStats,
    AreaLite,
    AreaMemberRow,
)


class NotAllowed(Exception):
    pass


async def administered_area_ids(db: AsyncSession, user: User) -> list[int]:
    """Áreas que el usuario administra. Super admin -> todas."""
    ids = await admin_area_ids(db, user)
    if ids is None:
        ids = [r[0] for r in (await db.execute(select(Area.id))).all()]
    return ids


async def project_ids(db: AsyncSession, area_ids: list[int]) -> list[int]:
    if not area_ids:
        return []
    rows = await db.execute(select(Project.id).where(Project.area_id.in_(area_ids)))
    return [r[0] for r in rows.all()]


async def administered_project_ids(db: AsyncSession, user: User) -> list[int]:
    return await project_ids(db, await administered_area_ids(db, user))


async def scope(db: AsyncSession, user: User) -> AreaAdminScope:
    ids = await administered_area_ids(db, user)
    if not ids:
        return AreaAdminScope(areas=[])
    rows = (
        await db.execute(
            select(Area.id, Area.name, Area.slug).where(Area.id.in_(ids)).order_by(Area.name)
        )
    ).all()
    return AreaAdminScope(areas=[AreaLite(id=i, name=n, slug=s) for i, n, s in rows])


async def stats(db: AsyncSession, user: User) -> AreaAdminStats:
    ids = await administered_area_ids(db, user)
    if not ids:
        return AreaAdminStats(
            areas=0, projects=0, active_projects=0, tasks=0, open_tasks=0,
            overdue_tasks=0, members=0,
        )

    async def count(*where) -> int:
        stmt = select(func.count()).select_from(where[0])
        if len(where) > 1:
            stmt = stmt.where(*where[1:])
        return int((await db.execute(stmt)).scalar() or 0)

    proj_where = Project.area_id.in_(ids)
    pid_subq = select(Project.id).where(proj_where)
    return AreaAdminStats(
        areas=len(ids),
        projects=await count(Project, proj_where),
        active_projects=await count(Project, proj_where, Project.status == "active"),
        tasks=await count(Task, Task.project_id.in_(pid_subq)),
        open_tasks=await count(Task, Task.project_id.in_(pid_subq), Task.status != "done"),
        overdue_tasks=await count(
            Task,
            Task.project_id.in_(pid_subq),
            Task.status != "done",
            Task.due_date.is_not(None),
            Task.due_date < func.current_date(),
        ),
        members=int(
            (
                await db.execute(
                    select(func.count(func.distinct(UserArea.user_id))).where(
                        UserArea.area_id.in_(ids)
                    )
                )
            ).scalar()
            or 0
        ),
    )


async def activity(db: AsyncSession, user: User, *, limit: int = 10) -> AreaAdminActivity:
    ids = await administered_area_ids(db, user)
    if not ids:
        return AreaAdminActivity(recent_projects=[], recent_tasks=[])

    owner = aliased(User)
    proj_rows = (
        await db.execute(
            select(
                Project.id, Project.name, Project.status, Project.created_at, Area.name, owner.name
            )
            .join(Area, Area.id == Project.area_id)
            .outerjoin(owner, owner.id == Project.owner_id)
            .where(Project.area_id.in_(ids))
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
    ).all()
    recent_projects = [
        ActivityProject(id=pid, name=n, status=st, created_at=c, area_name=ar, owner_name=ow)
        for pid, n, st, c, ar, ow in proj_rows
    ]

    assignee = aliased(User)
    task_rows = (
        await db.execute(
            select(
                Task.id, Task.title, Task.status, Task.priority, Task.project_id,
                Task.created_at, Project.name, assignee.name,
            )
            .join(Project, Project.id == Task.project_id)
            .outerjoin(assignee, assignee.id == Task.assignee_id)
            .where(Project.area_id.in_(ids))
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
    ).all()
    recent_tasks = [
        ActivityTask(
            id=t, title=ti, status=st, priority=pr, project_id=pi,
            created_at=c, project_name=pn, assignee_name=an,
        )
        for t, ti, st, pr, pi, c, pn, an in task_rows
    ]
    return AreaAdminActivity(recent_projects=recent_projects, recent_tasks=recent_tasks)


async def members(db: AsyncSession, user: User) -> AreaAdminMembers:
    ids = await administered_area_ids(db, user)
    if not ids:
        return AreaAdminMembers(members=[])
    rows = (
        await db.execute(
            select(User.id, User.name, User.email, Area.id, Area.name, UserArea.area_role)
            .join(UserArea, UserArea.user_id == User.id)
            .join(Area, Area.id == UserArea.area_id)
            .where(UserArea.area_id.in_(ids))
            .order_by(Area.name, User.name)
        )
    ).all()
    return AreaAdminMembers(
        members=[
            AreaMemberRow(user_id=uid, name=n, email=e, area_id=ai, area_name=an, area_role=r)
            for uid, n, e, ai, an, r in rows
        ]
    )


async def _assert_administers(db: AsyncSession, user: User, area_id: int) -> None:
    if area_id not in await administered_area_ids(db, user):
        raise NotAllowed()


async def set_member(
    db: AsyncSession, user: User, area_id: int, target_user_id: int, area_role: str
) -> None:
    await _assert_administers(db, user, area_id)
    role = area_role if area_role in ("lead", "member") else "member"
    ua = await db.get(UserArea, {"user_id": target_user_id, "area_id": area_id})
    if ua is None:
        db.add(UserArea(user_id=target_user_id, area_id=area_id, area_role=role))
    else:
        ua.area_role = role
    target = await db.get(User, target_user_id)
    if target is not None and target.default_area_id is None:
        target.default_area_id = area_id
    await db.commit()


async def remove_member(
    db: AsyncSession, user: User, area_id: int, target_user_id: int
) -> None:
    await _assert_administers(db, user, area_id)
    ua = await db.get(UserArea, {"user_id": target_user_id, "area_id": area_id})
    if ua is not None:
        await db.delete(ua)
        await db.commit()
