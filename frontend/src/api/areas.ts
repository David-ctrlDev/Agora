import { api } from "./client";

export interface Area {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AreaCreate {
  name: string;
  description?: string | null;
}

export const listAreas = () => api.get<Area[]>("/api/areas");
export const createArea = (payload: AreaCreate) => api.post<Area>("/api/areas", payload);
