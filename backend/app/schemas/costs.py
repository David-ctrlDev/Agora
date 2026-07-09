from pydantic import BaseModel


class CostRow(BaseModel):
    key: str
    calls: int
    tokens: int
    cost_usd: float


class CostDay(BaseModel):
    day: str
    cost_usd: float
    tokens: int


class CostSummary(BaseModel):
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    month_cost_usd: float
    month_tokens: int
    month_calls: int
    input_rate_per_1m: float
    output_rate_per_1m: float
    by_day: list[CostDay]
    by_user: list[CostRow]
    by_model: list[CostRow]
