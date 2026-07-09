"""Agregados de consumo/costo del agente y gestión de tarifas por modelo."""
import calendar
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_token_usage import AgentTokenUsage as U
from app.models.model_pricing import ModelPricing
from app.models.user import User
from app.schemas.costs import (
    CostDay,
    CostMonth,
    CostRow,
    CostSummary,
    ModelPricingUpsert,
    TokenBreakdown,
)


async def summary(db: AsyncSession) -> CostSummary:
    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(U.cost_usd), 0.0),
                func.coalesce(func.sum(U.total_tokens), 0),
                func.count(),
            )
        )
    ).one()

    today = date.today()
    first_of_month = today.replace(day=1)
    month = (
        await db.execute(
            select(
                func.coalesce(func.sum(U.cost_usd), 0.0),
                func.coalesce(func.sum(U.total_tokens), 0),
                func.count(),
            ).where(func.date(U.created_at) >= first_of_month)
        )
    ).one()
    # Proyección del mes: costo acumulado / días transcurridos × días del mes.
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    projection = float(month[0] or 0) / today.day * days_in_month

    # Desglose de tokens (entrada sin caché / caché / salida / pensamiento / herramientas).
    bd = (
        await db.execute(
            select(
                func.coalesce(func.sum(U.prompt_tokens - U.cached_tokens), 0),
                func.coalesce(func.sum(U.cached_tokens), 0),
                func.coalesce(func.sum(U.output_tokens), 0),
                func.coalesce(func.sum(U.thought_tokens), 0),
                func.coalesce(func.sum(U.tool_tokens), 0),
            )
        )
    ).one()
    classified = int(bd[0] or 0) + int(bd[1] or 0) + int(bd[2] or 0) + int(bd[3] or 0) + int(bd[4] or 0)
    # Residuo: lo que el total de Google trae por encima de lo desglosado (p. ej.
    # filas registradas antes de capturar herramientas). Así la dona siempre cuadra.
    others = max(0, int(totals[1] or 0) - classified)
    breakdown = TokenBreakdown(
        input=int(bd[0] or 0),
        cached=int(bd[1] or 0),
        output=int(bd[2] or 0),
        thoughts=int(bd[3] or 0),
        tools=int(bd[4] or 0),
        others=others,
    )

    # Últimos 12 meses.
    months_back = today.year * 12 + (today.month - 1) - 11
    m_year, m_month = divmod(months_back, 12)
    twelve_months_ago = date(m_year, m_month + 1, 1)
    month_expr = func.to_char(U.created_at, "YYYY-MM")
    month_rows = (
        await db.execute(
            select(month_expr, func.sum(U.cost_usd), func.sum(U.total_tokens))
            .where(func.date(U.created_at) >= twelve_months_ago)
            .group_by(month_expr)
            .order_by(month_expr)
        )
    ).all()
    by_month = [
        CostMonth(month=m, cost_usd=round(float(c or 0), 4), tokens=int(t or 0))
        for m, c, t in month_rows
    ]

    since = today - timedelta(days=29)
    day_rows = (
        await db.execute(
            select(func.date(U.created_at), func.sum(U.cost_usd), func.sum(U.total_tokens))
            .where(func.date(U.created_at) >= since)
            .group_by(func.date(U.created_at))
            .order_by(func.date(U.created_at))
        )
    ).all()
    by_day = [
        CostDay(day=str(d), cost_usd=round(float(c or 0), 4), tokens=int(t or 0))
        for d, c, t in day_rows
    ]

    user_rows = (
        await db.execute(
            select(User.name, func.count(), func.sum(U.total_tokens), func.sum(U.cost_usd))
            .select_from(U)
            .outerjoin(User, User.id == U.user_id)
            .group_by(User.name)
            .order_by(func.sum(U.cost_usd).desc())
        )
    ).all()
    by_user = [
        CostRow(
            key=name or "Sin usuario",
            calls=int(calls),
            tokens=int(tok or 0),
            cost_usd=round(float(cost or 0), 4),
        )
        for name, calls, tok, cost in user_rows
    ]

    model_rows = (
        await db.execute(
            select(U.model, func.count(), func.sum(U.total_tokens), func.sum(U.cost_usd))
            .group_by(U.model)
            .order_by(func.sum(U.cost_usd).desc())
        )
    ).all()
    by_model = [
        CostRow(
            key=model,
            calls=int(calls),
            tokens=int(tok or 0),
            cost_usd=round(float(cost or 0), 4),
        )
        for model, calls, tok, cost in model_rows
    ]

    return CostSummary(
        total_cost_usd=round(float(totals[0] or 0), 4),
        total_tokens=int(totals[1] or 0),
        total_calls=int(totals[2] or 0),
        month_cost_usd=round(float(month[0] or 0), 4),
        month_tokens=int(month[1] or 0),
        month_calls=int(month[2] or 0),
        month_projection_usd=round(projection, 4),
        breakdown=breakdown,
        by_day=by_day,
        by_month=by_month,
        by_user=by_user,
        by_model=by_model,
    )


# --- Tarifas por modelo (las gestiona el super admin) ---


async def list_pricing(db: AsyncSession) -> list[ModelPricing]:
    return list(
        (await db.execute(select(ModelPricing).order_by(ModelPricing.model))).scalars().all()
    )


async def upsert_pricing(db: AsyncSession, payload: ModelPricingUpsert) -> ModelPricing:
    model = payload.model.strip()
    row = (
        await db.execute(select(ModelPricing).where(ModelPricing.model == model))
    ).scalar_one_or_none()
    if row is None:
        row = ModelPricing(
            model=model,
            input_per_1m=payload.input_per_1m,
            output_per_1m=payload.output_per_1m,
            cached_per_1m=payload.cached_per_1m,
        )
        db.add(row)
    else:
        row.input_per_1m = payload.input_per_1m
        row.output_per_1m = payload.output_per_1m
        row.cached_per_1m = payload.cached_per_1m
    await db.commit()
    await db.refresh(row)
    return row


async def delete_pricing(db: AsyncSession, pricing_id: int) -> bool:
    row = await db.get(ModelPricing, pricing_id)
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True
