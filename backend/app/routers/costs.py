from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_costs_access, require_superadmin
from app.schemas.costs import CostSummary, ModelPricingRead, ModelPricingUpsert
from app.services import costs as svc

router = APIRouter(
    prefix="/api/costs", tags=["costs"], dependencies=[Depends(require_costs_access)]
)


@router.get("/summary", response_model=CostSummary)
async def cost_summary(db: AsyncSession = Depends(get_db)) -> CostSummary:
    return await svc.summary(db)


@router.get("/pricing", response_model=list[ModelPricingRead])
async def list_pricing(db: AsyncSession = Depends(get_db)) -> list[ModelPricingRead]:
    return await svc.list_pricing(db)


@router.put(
    "/pricing",
    response_model=ModelPricingRead,
    dependencies=[Depends(require_superadmin)],
)
async def upsert_pricing(
    payload: ModelPricingUpsert, db: AsyncSession = Depends(get_db)
) -> ModelPricingRead:
    """Crea o actualiza la tarifa de un modelo. Solo super admin."""
    return await svc.upsert_pricing(db, payload)


@router.delete(
    "/pricing/{pricing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_superadmin)],
)
async def delete_pricing(pricing_id: int, db: AsyncSession = Depends(get_db)) -> None:
    if not await svc.delete_pricing(db, pricing_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarifa no encontrada")
