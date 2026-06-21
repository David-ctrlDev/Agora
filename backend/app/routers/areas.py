from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.area import Area
from app.schemas.area import AreaCreate, AreaRead
from app.services import areas as areas_service

router = APIRouter(prefix="/api/areas", tags=["areas"])


@router.get("", response_model=list[AreaRead])
async def list_areas(db: AsyncSession = Depends(get_db)) -> list[Area]:
    return await areas_service.list_areas(db)


@router.post("", response_model=AreaRead, status_code=status.HTTP_201_CREATED)
async def create_area(payload: AreaCreate, db: AsyncSession = Depends(get_db)) -> Area:
    try:
        return await areas_service.create_area(db, payload)
    except areas_service.AreaSlugExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
