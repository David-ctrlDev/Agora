import { api } from "./client";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

export interface ProjectAnalytics {
  project_id: number;
  name: string;
  status: string;
  total: number;
  done: number;
  open: number;
  blocked: number;
  overdue: number;
  completion_pct: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  health: string;
  due_date: string | null;
  due_in_days: number | null;
  area_name: string | null;
  category: string | null;
  criticality: string | null;
  project_type: string | null;
  initiative: string | null;
  process: string | null;
}

export interface OverviewTotals {
  projects: number;
  active_projects: number;
  total_tasks: number;
  done_tasks: number;
  completion_pct: number;
  overdue_tasks: number;
  at_risk_projects: number;
}

export interface AreaStat {
  area: string;
  projects: number;
  completion_pct: number;
  at_risk: number;
}

export interface Overview {
  projects: ProjectAnalytics[];
  totals: OverviewTotals;
  by_area: AreaStat[];
  task_by_status: Record<string, number>;
  project_by_status: Record<string, number>;
  by_criticality: Record<string, number>;
}

export const getProjectAnalytics = (id: number) =>
  api.get<ProjectAnalytics>(`/api/projects/${id}/analytics`);
export const getOverview = () => api.get<Overview>("/api/analytics/overview");

export const HEALTH: Record<string, { label: string; tone: Tone }> = {
  sin_tareas: { label: "Sin tareas", tone: "neutral" },
  en_curso: { label: "En curso", tone: "brand" },
  atencion: { label: "Atención", tone: "warning" },
  en_riesgo: { label: "En riesgo", tone: "danger" },
  completado: { label: "Completado", tone: "success" },
};

export const STATUS_META: Record<string, { label: string; color: string }> = {
  todo: { label: "Por hacer", color: "#cbd5e1" },
  in_progress: { label: "En progreso", color: "#0ea5e9" },
  blocked: { label: "Bloqueada", color: "#f59e0b" },
  done: { label: "Hecha", color: "#10b981" },
};

export const PRIORITY_META: Record<string, { label: string; color: string }> = {
  high: { label: "Alta", color: "#ef4444" },
  medium: { label: "Media", color: "#f59e0b" },
  low: { label: "Baja", color: "#94a3b8" },
};

export const PROJECT_STATUS_META: Record<string, { label: string; color: string }> = {
  planned: { label: "Planeado", color: "#94a3b8" },
  active: { label: "Activo", color: "#10b981" },
  on_hold: { label: "En pausa", color: "#f59e0b" },
  done: { label: "Terminado", color: "#047857" },
  archived: { label: "Archivado", color: "#cbd5e1" },
};

export const CRITICALITY_META: Record<string, { label: string; color: string }> = {
  ALTA: { label: "Alta", color: "#ef4444" },
  MEDIA: { label: "Media", color: "#f59e0b" },
  BAJA: { label: "Baja", color: "#10b981" },
  "Sin definir": { label: "Sin definir", color: "#cbd5e1" },
};
