from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.catalog import CatalogTermRead
from app.services import catalog as svc

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog", response_model=list[CatalogTermRead])
async def list_catalog(
    kind: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CatalogTermRead]:
    """Valores activos de una maestra (process|category|project_type) para elegir."""
    try:
        return await svc.list_terms(db, kind, active_only=True)
    except svc.InvalidKind:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="kind inválido") from None
