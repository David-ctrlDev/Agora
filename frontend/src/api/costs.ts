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

export interface CostMonth {
  month: string;
  cost_usd: number;
  tokens: number;
}

export interface TokenBreakdown {
  input: number;
  cached: number;
  output: number;
  thoughts: number;
  tools: number;
  others: number;
}

export interface CostSummary {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  month_cost_usd: number;
  month_tokens: number;
  month_calls: number;
  month_projection_usd: number;
  breakdown: TokenBreakdown;
  by_day: CostDay[];
  by_month: CostMonth[];
  by_user: CostRow[];
  by_model: CostRow[];
}

export interface ModelPricing {
  id: number;
  model: string;
  input_per_1m: number;
  output_per_1m: number;
  cached_per_1m: number | null;
}

export const getCostSummary = () => api.get<CostSummary>("/api/costs/summary");
export const getPricing = () => api.get<ModelPricing[]>("/api/costs/pricing");
export const upsertPricing = (payload: {
  model: string;
  input_per_1m: number;
  output_per_1m: number;
  cached_per_1m: number | null;
}) => api.put<ModelPricing>("/api/costs/pricing", payload);
export const deletePricing = (id: number) => api.del<void>(`/api/costs/pricing/${id}`);
