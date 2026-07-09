from pydantic import BaseModel, ConfigDict, Field


class CostRow(BaseModel):
    key: str
    calls: int
    tokens: int
    cost_usd: float


class CostDay(BaseModel):
    day: str
    cost_usd: float
    tokens: int


class CostMonth(BaseModel):
    month: str  # "2026-07"
    cost_usd: float
    tokens: int


class TokenBreakdown(BaseModel):
    input: int  # entrada sin caché
    cached: int  # contexto cacheado
    output: int  # respuesta
    thoughts: int  # razonamiento
    tools: int  # herramientas (tool_use_prompt)
    others: int  # residuo del total reportado por Google aún sin desglosar


class CostSummary(BaseModel):
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    month_cost_usd: float
    month_tokens: int
    month_calls: int
    month_projection_usd: float  # proyección del mes al ritmo actual
    breakdown: TokenBreakdown
    by_day: list[CostDay]
    by_month: list[CostMonth]
    by_user: list[CostRow]
    by_model: list[CostRow]


class ModelPricingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str
    input_per_1m: float
    output_per_1m: float
    cached_per_1m: float | None = None


class ModelPricingUpsert(BaseModel):
    model: str = Field(min_length=1, max_length=80)
    input_per_1m: float = Field(ge=0)
    output_per_1m: float = Field(ge=0)
    # Tarifa del contexto cacheado; None => se cobra como entrada normal.
    cached_per_1m: float | None = Field(default=None, ge=0)
