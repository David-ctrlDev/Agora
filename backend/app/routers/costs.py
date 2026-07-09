from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_costs_access
from app.schemas.costs import CostSummary
from app.services import costs as svc

router = APIRouter(
    prefix="/api/costs", tags=["costs"], dependencies=[Depends(require_costs_access)]
)


@router.get("/summary", response_model=CostSummary)
async def cost_summary(db: AsyncSession = Depends(get_db)) -> CostSummary:
    return await svc.summary(db)
