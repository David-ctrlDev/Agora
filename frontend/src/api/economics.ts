import { api } from "./client";

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
  has_data: boolean;
}

export interface EconomicsUpdate {
  estimated_cost?: number | null;
  actual_cost?: number | null;
  expected_benefit?: number | null;
  actual_benefit?: number | null;
  currency?: string;
}

export const getEconomics = (id: number) =>
  api.get<ProjectEconomics>(`/api/projects/${id}/economics`);
export const updateEconomics = (id: number, payload: EconomicsUpdate) =>
  api.patch<ProjectEconomics>(`/api/projects/${id}/economics`, payload);
