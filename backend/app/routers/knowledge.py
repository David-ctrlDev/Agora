from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.rag.extract import UnsupportedFile, extract_text
from app.schemas.knowledge import (
    DocumentCreate,
    DocumentDetail,
    DocumentRead,
    SearchQuery,
    SearchResult,
)
from app.services import knowledge as svc
from app.services import projects as projects_svc

router = APIRouter(prefix="/api", tags=["knowledge"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


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
    return await svc.ingest_document(
        db, project_id, payload.title, payload.content, source=payload.source
    )


@router.post(
    "/projects/{project_id}/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    source: str = Form(default="file"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    await _project(project_id, user, db, edit=True)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 15 MB",
        )
    try:
        text = extract_text(file.filename or "archivo", file.content_type, data)
    except UnsupportedFile as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo extraer texto del archivo.",
        )
    doc_title = (title or file.filename or "Documento").strip()
    return await svc.ingest_document(
        db,
        project_id,
        doc_title,
        text,
        source=source,
        file_name=file.filename,
        mime_type=file.content_type,
        file_data=data,
    )


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


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document_detail(
    document_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Document:
    document = await svc.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    await _project(document.project_id, user, db)
    return document


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    document = await svc.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    await _project(document.project_id, user, db)
    if document.file_data:
        return Response(
            content=document.file_data,
            media_type=document.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{document.file_name or "documento"}"'},
        )
    return Response(
        content=(document.content_text or "").encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{document.title}.txt"'},
    )


@router.post("/knowledge/search", response_model=list[SearchResult])
async def search(
    payload: SearchQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    project_ids = await projects_svc.accessible_project_ids(db, user)
    return await svc.search(db, payload.query, project_ids)
