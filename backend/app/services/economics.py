"""Economía del proyecto: costos, beneficios y ROI calculado."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.economics import EconomicsUpdate, ProjectEconomics


def _pct(numerator: float, denominator: float | None) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator * 100, 1)


def compute(project: Project) -> ProjectEconomics:
    ec = project.estimated_cost
    ac = project.actual_cost
    eb = project.expected_benefit
    ab = project.actual_benefit
    return ProjectEconomics(
        currency=project.currency,
        estimated_cost=ec,
        actual_cost=ac,
        expected_benefit=eb,
        actual_benefit=ab,
        net_expected=(eb - ec) if (eb is not None and ec is not None) else None,
        net_actual=(ab - ac) if (ab is not None and ac is not None) else None,
        roi_expected_pct=_pct(eb - ec, ec) if (eb is not None and ec) else None,
        roi_actual_pct=_pct(ab - ac, ac) if (ab is not None and ac) else None,
        cost_consumption_pct=_pct(ac, ec) if (ac is not None and ec) else None,
        benefit_realization_pct=_pct(ab, eb) if (ab is not None and eb) else None,
        has_data=any(v is not None for v in (ec, ac, eb, ab)),
    )


async def update_economics(
    db: AsyncSession, project: Project, payload: EconomicsUpdate
) -> ProjectEconomics:
    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key, value in data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return compute(project)
