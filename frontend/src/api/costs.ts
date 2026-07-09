import { api } from "./client";

export interface CostRow {
  key: string;
  calls: number;
  tokens: number;
  cost_usd: number;
}

export interface CostDay {
  day: string;
  cost_usd: number;
  tokens: number;
}

export interface CostSummary {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  month_cost_usd: number;
  month_tokens: number;
  month_calls: number;
  input_rate_per_1m: number;
  output_rate_per_1m: number;
  by_day: CostDay[];
  by_user: CostRow[];
  by_model: CostRow[];
}

export const getCostSummary = () => api.get<CostSummary>("/api/costs/summary");
