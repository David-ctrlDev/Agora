from pydantic import BaseModel, Field


class EconomicsUpdate(BaseModel):
    estimated_cost: float | None = Field(default=None, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    expected_benefit: float | None = Field(default=None, ge=0)
    actual_benefit: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ProjectEconomics(BaseModel):
    currency: str
    estimated_cost: float | None
    actual_cost: float | None
    expected_benefit: float | None
    actual_benefit: float | None
    net_expected: float | None
    net_actual: float | None
    roi_expected_pct: float | None
    roi_actual_pct: float | None
    cost_consumption_pct: float | None
    benefit_realization_pct: float | None
    has_data: bool
