from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["low", "medium", "high"]


class EconomicsUpdate(BaseModel):
    # Monetario (ejecutor: costos · beneficiario: beneficios).
    estimated_cost: float | None = Field(default=None, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    expected_benefit: float | None = Field(default=None, ge=0)
    actual_benefit: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    # Lado ejecutor (el proceso que lo hace): inversión no monetaria.
    effort_hours_estimated: float | None = Field(default=None, ge=0)
    effort_hours_actual: float | None = Field(default=None, ge=0)
    executor_team: str | None = Field(default=None, max_length=200)
    implementation_complexity: Level | None = None
    resources_needed: str | None = None
    # Lado beneficiario (el proceso para el que se hace): retorno no monetario.
    beneficiary_area_id: int | None = None
    beneficiary_process: str | None = Field(default=None, max_length=160)
    hours_saved_monthly: float | None = Field(default=None, ge=0)
    people_impacted: int | None = Field(default=None, ge=0)
    risk_reduction: Level | None = None
    strategic_value: Level | None = None


class ProjectEconomics(BaseModel):
    currency: str
    # Monetario + métricas derivadas.
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
    # Lado ejecutor (el proceso que lo hace).
    executor_area_id: int | None
    executor_process: str | None
    effort_hours_estimated: float | None
    effort_hours_actual: float | None
    effort_variance_pct: float | None
    executor_team: str | None
    implementation_complexity: str | None
    resources_needed: str | None
    # Lado beneficiario (el proceso para el que se hace).
    beneficiary_area_id: int | None
    beneficiary_process: str | None
    hours_saved_monthly: float | None
    hours_saved_yearly: float | None
    people_impacted: int | None
    risk_reduction: str | None
    strategic_value: str | None
    has_data: bool
    has_impact: bool
