"""Documentación del proyecto como carpeta en Drive (creada por el owner, compartida con los miembros).

Ágora es el espejo + vectorizador; Drive es el repositorio visible cuando hay conexión.
Todo es "best-effort": si Drive falla o no hay conexión, el proyecto sigue funcionando local.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.google import real_api
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.services import google as google_service


def enabled() -> bool:
    """La sincronización con Drive solo opera con proveedor real y la feature activada."""
    return settings.drive_docs_enabled and settings.google_provider == "real"


async def _owner_access(db: AsyncSession, project: Project) -> str | None:
    if project.owner_id is None:
        return None
    owner = await db.get(User, project.owner_id)
    if owner is None:
        return None
    return await google_service.get_access_token(db, owner)


async def _member_emails(db: AsyncSession, project: Project) -> list[str]:
    rows = (
        await db.execute(
            select(User.email)
            .join(ProjectMember, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == project.id)
        )
    ).scalars().all()
    return [e for e in rows if e]


async def share_with_members(
    db: AsyncSession, project: Project, access: str, folder_id: str | None = None
) -> None:
    """Comparte la carpeta del proyecto (como editores) con los miembros que haya en Ágora."""
    folder_id = folder_id or project.docs_folder_id
    if not folder_id:
        return
    for email in await _member_emails(db, project):
        try:
            await real_api.share_file(access, folder_id, email, "writer")
        except Exception:
            pass


async def ensure_project_folder(
    db: AsyncSession, project: Project, access: str | None = None
) -> str | None:
    """Crea (si falta) la carpeta `Ágora / {Proyecto}` en el Drive del owner y la comparte.

    Devuelve el id de la carpeta, o None si Drive no está disponible (entonces todo
    sigue viviendo solo en Ágora, que es la fuente de verdad/espejo).
    """
    if not enabled():
        return None
    if project.docs_folder_id:
        return project.docs_folder_id
    access = access or await _owner_access(db, project)
    if not access:
        return None
    try:
        root = await real_api.ensure_folder(access, "Ágora", settings.drive_docs_root_id or None)
        folder = await real_api.ensure_folder(access, project.name, root)
    except Exception:
        return None
    project.docs_folder_id = folder
    await db.commit()
    await db.refresh(project)
    await share_with_members(db, project, access, folder)
    return folder
