import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.integrations.github.webhook import parse_webhook, verify_signature
from app.models.github_repo import GitHubRepo
from app.models.project import Project
from app.models.user import User
from app.schemas.github import GitHubEventRead, GitHubRepoCreate, GitHubRepoRead
from app.services import github as svc
from app.services import projects as projects_svc

router = APIRouter(prefix="/api", tags=["github"])


async def _project(project_id: int, user: User, db: AsyncSession, *, edit: bool = False) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


async def _repo_for_edit(repo_id: int, user: User, db: AsyncSession) -> GitHubRepo:
    repo = await svc.get_repo(db, repo_id)
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositorio no encontrado")
    await _project(repo.project_id, user, db, edit=True)
    return repo


@router.get("/projects/{project_id}/github/repos", response_model=list[GitHubRepoRead])
async def list_repos(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[GitHubRepo]:
    await _project(project_id, user, db)
    return await svc.list_repos(db, project_id)


@router.post(
    "/projects/{project_id}/github/repos",
    response_model=GitHubRepoRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_repo(
    project_id: int,
    payload: GitHubRepoCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GitHubRepo:
    await _project(project_id, user, db, edit=True)
    try:
        return await svc.link_repo(db, project_id, payload.full_name)
    except svc.RepoAlreadyLinked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ese repositorio ya está vinculado"
        ) from exc


@router.delete("/github/repos/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_repo(
    repo_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    repo = await _repo_for_edit(repo_id, user, db)
    await svc.unlink_repo(db, repo)


@router.post("/github/repos/{repo_id}/sync")
async def sync_repo(
    repo_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    repo = await _repo_for_edit(repo_id, user, db)
    return {"new_events": await svc.sync_repo(db, repo)}


@router.get("/projects/{project_id}/github/activity", response_model=list[GitHubEventRead])
async def activity(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list:
    await _project(project_id, user, db)
    return await svc.list_project_activity(db, project_id)


@router.post("/github/webhook")
async def webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    body = await request.body()
    if not verify_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma inválida")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido") from exc
    full_name, event = parse_webhook(x_github_event, payload)
    if full_name is None or event is None:
        return {"ok": True, "stored": 0}
    return {"ok": True, "stored": await svc.store_webhook_event(db, full_name, event)}
