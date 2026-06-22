import { api } from "./client";

export type Level = "low" | "medium" | "high";

export interface ProjectEconomics {
  currency: string;
  estimated_cost: number | null;
  actual_cost: number | null;
  expected_benefit: number | null;
  actual_benefit: number | null;
  net_expected: number | null;
  net_actual: number | null;
  roi_expected_pct: number | null;
  roi_actual_pct: number | null;
  cost_consumption_pct: number | null;
  benefit_realization_pct: number | null;
  // Lado ejecutor (el proceso que lo hace).
  executor_area_id: number | null;
  executor_process: string | null;
  effort_hours_estimated: number | null;
  effort_hours_actual: number | null;
  effort_variance_pct: number | null;
  executor_team: string | null;
  implementation_complexity: Level | null;
  resources_needed: string | null;
  // Lado beneficiario (el proceso para el que se hace).
  beneficiary_area_id: number | null;
  beneficiary_process: string | null;
  hours_saved_monthly: number | null;
  hours_saved_yearly: number | null;
  people_impacted: number | null;
  risk_reduction: Level | null;
  strategic_value: Level | null;
  has_data: boolean;
  has_impact: boolean;
}

export interface EconomicsUpdate {
  estimated_cost?: number | null;
  actual_cost?: number | null;
  expected_benefit?: number | null;
  actual_benefit?: number | null;
  currency?: string;
  effort_hours_estimated?: number | null;
  effort_hours_actual?: number | null;
  executor_team?: string | null;
  implementation_complexity?: Level | null;
  resources_needed?: string | null;
  beneficiary_area_id?: number | null;
  beneficiary_process?: string | null;
  hours_saved_monthly?: number | null;
  people_impacted?: number | null;
  risk_reduction?: Level | null;
  strategic_value?: Level | null;
}

export const getEconomics = (id: number) =>
  api.get<ProjectEconomics>(`/api/projects/${id}/economics`);
export const updateEconomics = (id: number, payload: EconomicsUpdate) =>
  api.patch<ProjectEconomics>(`/api/projects/${id}/economics`, payload);
