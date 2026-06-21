import { api } from "./client";

export type SprintStatus = "planned" | "active" | "completed";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

export const SPRINT_STATUS: Record<string, { label: string; tone: Tone }> = {
  planned: { label: "Planeado", tone: "neutral" },
  active: { label: "Activo", tone: "brand" },
  completed: { label: "Completado", tone: "success" },
};

export interface Sprint {
  id: number;
  project_id: number;
  name: string;
  goal: string | null;
  start_date: string;
  end_date: string;
  status: string;
  created_at: string;
  total: number;
  done: number;
  completion_pct: number;
}

export interface SprintCreate {
  name: string;
  goal?: string | null;
  start_date: string;
  end_date: string;
  status?: SprintStatus;
}

export interface SprintUpdate {
  name?: string;
  goal?: string | null;
  start_date?: string;
  end_date?: string;
  status?: SprintStatus;
}

export interface BurndownPoint {
  date: string;
  ideal: number;
  remaining: number | null;
}

export interface Burndown {
  sprint_id: number;
  total: number;
  points: BurndownPoint[];
}

export const listSprints = (projectId: number) =>
  api.get<Sprint[]>(`/api/projects/${projectId}/sprints`);
export const createSprint = (projectId: number, payload: SprintCreate) =>
  api.post<Sprint>(`/api/projects/${projectId}/sprints`, payload);
export const updateSprint = (sprintId: number, payload: SprintUpdate) =>
  api.patch<Sprint>(`/api/sprints/${sprintId}`, payload);
export const deleteSprint = (sprintId: number) => api.del<void>(`/api/sprints/${sprintId}`);
export const getBurndown = (sprintId: number) =>
  api.get<Burndown>(`/api/sprints/${sprintId}/burndown`);
