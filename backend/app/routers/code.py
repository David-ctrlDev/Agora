"""Pestaña Código: historial de versiones Git para proyectos de desarrollo.

Todas las rutas validan en el backend: acceso por área al proyecto, que el
proyecto sea de desarrollo, y permiso de edición para las escrituras.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.code import (
    BranchCreate,
    ChangedFile,
    CodeStatus,
    CommitInfo,
    DiffResult,
    GitignoreState,
    GitignoreUpdate,
    MergeRequest,
    RestoreRequest,
)
from app.services import coderepo
from app.services import projects as projects_svc

router = APIRouter(prefix="/api/projects/{project_id}/code", tags=["code"])


async def _dev_project(
    project_id: int, user: User, db: AsyncSession, *, edit: bool = False
) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if not project.is_development:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este proyecto no es de desarrollo"
        )
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


def _err(exc: coderepo.CodeRepoError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/status", response_model=CodeStatus)
async def code_status(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CodeStatus:
    await _dev_project(project_id, user, db)
    return CodeStatus(**(await coderepo.status(project_id)))


@router.get("/commits", response_model=list[CommitInfo])
async def commits(
    project_id: int,
    branch: str = "main",
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommitInfo]:
    await _dev_project(project_id, user, db)
    rows = await coderepo.history(project_id, branch, min(max(limit, 1), 100))
    return [CommitInfo(**r) for r in rows]


@router.get("/commits/{ref}/files", response_model=list[ChangedFile])
async def commit_files(
    project_id: int,
    ref: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChangedFile]:
    await _dev_project(project_id, user, db)
    try:
        return [ChangedFile(**r) for r in await coderepo.commit_detail(project_id, ref)]
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None


@router.get("/zip")
async def download_zip(
    project_id: int,
    ref: str = "main",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    project = await _dev_project(project_id, user, db)
    try:
        data = await coderepo.archive_zip(project_id, ref)
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None
    name = f"{project.name[:40].replace(' ', '_')}-{ref[:12]}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/upload", response_model=CommitInfo)
async def upload(
    project_id: int,
    files: list[UploadFile] = File(...),
    message: str = Form(""),
    branch: str = Form("main"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitInfo:
    project = await _dev_project(project_id, user, db, edit=True)
    payload: list[tuple[str, bytes]] = []
    for f in files:
        payload.append((f.filename or "archivo", await f.read()))
    try:
        info = await coderepo.commit_upload(project, user, payload, message, branch)
    except coderepo.NoChanges as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None
    return CommitInfo(**info)


@router.post("/restore", response_model=CommitInfo)
async def restore(
    project_id: int,
    payload: RestoreRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitInfo:
    project = await _dev_project(project_id, user, db, edit=True)
    try:
        info = await coderepo.restore(project, user, payload.hash, payload.branch)
    except coderepo.NoChanges as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None
    return CommitInfo(**info)


@router.get("/gitignore", response_model=GitignoreState)
async def gitignore_state(
    project_id: int,
    branch: str = "main",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GitignoreState:
    await _dev_project(project_id, user, db)
    return GitignoreState(**(await coderepo.get_gitignore(project_id, branch)))


@router.put("/gitignore", response_model=CommitInfo)
async def gitignore_update(
    project_id: int,
    payload: GitignoreUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitInfo:
    project = await _dev_project(project_id, user, db, edit=True)
    try:
        info = await coderepo.set_gitignore(project, user, payload.categories, payload.extra)
    except coderepo.NoChanges as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None
    return CommitInfo(**info)


# ─────────────────────────── Borradores (fase 2) ───────────────────────────


@router.post("/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(
    project_id: int,
    payload: BranchCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    project = await _dev_project(project_id, user, db, edit=True)
    try:
        return await coderepo.create_branch(project, payload.name)
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None


@router.delete("/branches/{branch}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    project_id: int,
    branch: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    project = await _dev_project(project_id, user, db, edit=True)
    try:
        await coderepo.delete_branch(project, branch)
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None


@router.get("/branches/{branch}/diff", response_model=DiffResult)
async def branch_diff(
    project_id: int,
    branch: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiffResult:
    await _dev_project(project_id, user, db)
    try:
        return DiffResult(**(await coderepo.diff_vs_main(project_id, branch)))
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None


@router.post("/merge", response_model=CommitInfo)
async def merge(
    project_id: int,
    payload: MergeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitInfo:
    project = await _dev_project(project_id, user, db, edit=True)
    try:
        info = await coderepo.merge_branch(
            project, user, payload.branch, payload.message, payload.resolutions
        )
    except coderepo.MergeConflicts as exc:
        # 409 con la lista de archivos en conflicto: el frontend abre el resolutor.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"conflicts": exc.files},
        ) from None
    except coderepo.CodeRepoError as exc:
        raise _err(exc) from None
    return CommitInfo(**info)
