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
    he = project.effort_hours_estimated
    ha = project.effort_hours_actual
    hsm = project.hours_saved_monthly
    impact_fields = (
        he,
        ha,
        project.executor_team,
        project.implementation_complexity,
        project.resources_needed,
        project.beneficiary_area_id,
        project.beneficiary_process,
        hsm,
        project.people_impacted,
        project.risk_reduction,
        project.strategic_value,
    )
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
        # Lado ejecutor (el proceso que lo hace).
        executor_area_id=project.area_id,
        executor_process=project.process,
        effort_hours_estimated=he,
        effort_hours_actual=ha,
        effort_variance_pct=_pct(ha - he, he) if (ha is not None and he) else None,
        executor_team=project.executor_team,
        implementation_complexity=project.implementation_complexity,
        resources_needed=project.resources_needed,
        # Lado beneficiario (el proceso para el que se hace).
        beneficiary_area_id=project.beneficiary_area_id,
        beneficiary_process=project.beneficiary_process,
        hours_saved_monthly=hsm,
        hours_saved_yearly=round(hsm * 12, 1) if hsm is not None else None,
        people_impacted=project.people_impacted,
        risk_reduction=project.risk_reduction,
        strategic_value=project.strategic_value,
        has_data=any(v is not None for v in (ec, ac, eb, ab)),
        has_impact=any(v is not None for v in impact_fields),
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
