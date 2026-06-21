from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_user_area_ids
from app.models.area import Area
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectMemberRead, ProjectRead, ProjectUpdate


class AreaNotAllowed(Exception):
    """El usuario no pertenece al área del proyecto que intenta crear."""


def _to_read(project: Project, area_name: str | None, owner_name: str | None) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        area_id=project.area_id,
        status=project.status,
        owner_id=project.owner_id,
        start_date=project.start_date,
        due_date=project.due_date,
        progress=project.progress,
        created_at=project.created_at,
        updated_at=project.updated_at,
        area_name=area_name,
        owner_name=owner_name,
        initiative=project.initiative,
        proposed_by=project.proposed_by,
        project_type=project.project_type,
        category=project.category,
        criticality=project.criticality,
        process=project.process,
        benefits=project.benefits,
        change_management=project.change_management,
    )


async def accessible_project_ids(db: AsyncSession, user: User) -> list[int]:
    """IDs de proyectos accesibles por el usuario (área o membresía de proyecto)."""
    area_ids = await get_user_area_ids(db, user)
    stmt = select(Project.id)
    if area_ids is not None:
        member_pids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(or_(Project.area_id.in_(area_ids), Project.id.in_(member_pids)))
    return [row[0] for row in (await db.execute(stmt)).all()]


async def list_projects(db: AsyncSession, user: User) -> list[ProjectRead]:
    stmt = (
        select(Project, Area.name, User.name)
        .join(Area, Area.id == Project.area_id)
        .outerjoin(User, User.id == Project.owner_id)
    )
    area_ids = await get_user_area_ids(db, user)
    if area_ids is not None:
        member_pids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(or_(Project.area_id.in_(area_ids), Project.id.in_(member_pids)))
    stmt = stmt.order_by(Project.created_at.desc())
    rows = (await db.execute(stmt)).all()
    return [_to_read(p, area_name, owner_name) for (p, area_name, owner_name) in rows]


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    return await db.get(Project, project_id)


async def can_access(db: AsyncSession, user: User, project: Project) -> bool:
    if user.role == "admin":
        return True
    area_ids = await get_user_area_ids(db, user)
    if area_ids and project.area_id in area_ids:
        return True
    member = await db.get(ProjectMember, {"project_id": project.id, "user_id": user.id})
    return member is not None


async def can_edit(db: AsyncSession, user: User, project: Project) -> bool:
    if user.role == "admin" or project.owner_id == user.id:
        return True
    member = await db.get(ProjectMember, {"project_id": project.id, "user_id": user.id})
    return member is not None and member.role in ("owner", "editor")


async def to_read(db: AsyncSession, project: Project) -> ProjectRead:
    area = await db.get(Area, project.area_id)
    owner = await db.get(User, project.owner_id) if project.owner_id else None
    return _to_read(project, area.name if area else None, owner.name if owner else None)


async def create_project(db: AsyncSession, user: User, payload: ProjectCreate) -> ProjectRead:
    area_ids = await get_user_area_ids(db, user)
    if area_ids is not None and payload.area_id not in area_ids:
        raise AreaNotAllowed()
    project = Project(
        name=payload.name.strip(),
        description=payload.description or None,
        area_id=payload.area_id,
        status=payload.status,
        owner_id=user.id,
        start_date=payload.start_date,
        due_date=payload.due_date,
        progress=payload.progress,
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(project)
    # Se crea un repositorio por debajo (sin UI); el usuario solo verá versiones de documentos.
    from app.services import github as github_svc

    await github_svc.ensure_repo_for_project(db, project)
    return await to_read(db, project)


async def update_project(db: AsyncSession, project: Project, payload: ProjectUpdate) -> ProjectRead:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return await to_read(db, project)


async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()


async def list_members(db: AsyncSession, project_id: int) -> list[ProjectMemberRead]:
    rows = (
        await db.execute(
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.name)
        )
    ).all()
    return [
        ProjectMemberRead(user_id=u.id, name=u.name, email=u.email, role=pm.role) for (pm, u) in rows
    ]


async def add_member(db: AsyncSession, project_id: int, user_id: int, role: str) -> None:
    member = await db.get(ProjectMember, {"project_id": project_id, "user_id": user_id})
    if member is not None:
        member.role = role
    else:
        db.add(ProjectMember(project_id=project_id, user_id=user_id, role=role))
    await db.commit()


async def remove_member(db: AsyncSession, project_id: int, user_id: int) -> None:
    member = await db.get(ProjectMember, {"project_id": project_id, "user_id": user_id})
    if member is not None:
        await db.delete(member)
        await db.commit()
