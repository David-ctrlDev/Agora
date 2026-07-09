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


class CostSummary(BaseModel):
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    month_cost_usd: float
    month_tokens: int
    month_calls: int
    by_day: list[CostDay]
    by_user: list[CostRow]
    by_model: list[CostRow]


class ModelPricingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str
    input_per_1m: float
    output_per_1m: float


class ModelPricingUpsert(BaseModel):
    model: str = Field(min_length=1, max_length=80)
    input_per_1m: float = Field(ge=0)
    output_per_1m: float = Field(ge=0)
