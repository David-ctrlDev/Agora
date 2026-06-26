from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.area_request import AreaCatalogItem, AreaRequestRead, DecisionPayload, NewAreaRequestCreate
from app.services import area_requests as svc
from app.services import areas as areas_service

router = APIRouter(tags=["areas"])


@router.get("/api/areas/catalog", response_model=list[AreaCatalogItem])
async def area_catalog(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AreaCatalogItem]:
    """Todas las áreas activas, con miembros/líderes y si ya eres miembro o tienes
    una solicitud pendiente. Accesible a cualquier usuario (para auto-unirse)."""
    return await svc.catalog(db, user)


@router.post("/api/areas/{area_id}/join", response_model=AreaRequestRead)
async def request_join(
    area_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AreaRequestRead:
    try:
        return await svc.request_join(db, user, area_id)
    except svc.AreaNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada") from None
    except svc.AlreadyMember:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya eres miembro de esa área") from None


@router.post("/api/area-requests/new-area", response_model=AreaRequestRead)
async def request_new_area(
    payload: NewAreaRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AreaRequestRead:
    return await svc.request_new_area(db, user, payload.name, payload.description)


@router.get("/api/area-requests/mine", response_model=list[AreaRequestRead])
async def my_requests(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AreaRequestRead]:
    return await svc.my_requests(db, user)


@router.get("/api/area-requests/pending", response_model=list[AreaRequestRead])
async def pending_requests(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AreaRequestRead]:
    """Solicitudes que el usuario puede aprobar (líder del área o admin global)."""
    return await svc.pending_for(db, user)


@router.post("/api/area-requests/{request_id}/approve", response_model=AreaRequestRead)
async def approve_request(
    request_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AreaRequestRead:
    try:
        return await svc.approve(db, user, request_id)
    except svc.RequestNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada") from None
    except svc.AlreadyDecided:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La solicitud ya fue resuelta") from None
    except svc.NotAllowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes aprobar esta solicitud") from None
    except areas_service.AreaSlugExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un área con ese nombre") from None


@router.post("/api/area-requests/{request_id}/reject", response_model=AreaRequestRead)
async def reject_request(
    request_id: int,
    payload: DecisionPayload | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AreaRequestRead:
    try:
        return await svc.reject(db, user, request_id, payload.note if payload else None)
    except svc.RequestNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada") from None
    except svc.AlreadyDecided:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La solicitud ya fue resuelta") from None
    except svc.NotAllowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes rechazar esta solicitud") from None
