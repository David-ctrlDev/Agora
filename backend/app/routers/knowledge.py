from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.schemas.knowledge import DocumentCreate, DocumentRead, SearchQuery, SearchResult
from app.services import knowledge as svc
from app.services import projects as projects_svc

router = APIRouter(prefix="/api", tags=["knowledge"])


async def _project(project_id: int, user: User, db: AsyncSession, *, edit: bool = False) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


@router.post(
    "/projects/{project_id}/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED
)
async def create_document(
    project_id: int,
    payload: DocumentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    await _project(project_id, user, db, edit=True)
    return await svc.ingest_document(db, project_id, payload.title, payload.content)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Document]:
    await _project(project_id, user, db)
    return await svc.list_documents(db, project_id)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    document = await svc.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    await _project(document.project_id, user, db, edit=True)
    await svc.delete_document(db, document)


@router.post("/knowledge/search", response_model=list[SearchResult])
async def search(
    payload: SearchQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    project_ids = await projects_svc.accessible_project_ids(db, user)
    return await svc.search(db, payload.query, project_ids)
