import { api } from "./client";

export type ProjectStatus = "planned" | "active" | "on_hold" | "done" | "archived";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

export const PROJECT_STATUS: Record<string, { label: string; tone: Tone }> = {
  planned: { label: "Planeado", tone: "neutral" },
  active: { label: "Activo", tone: "brand" },
  on_hold: { label: "En pausa", tone: "warning" },
  done: { label: "Terminado", tone: "success" },
  archived: { label: "Archivado", tone: "neutral" },
};

export interface RoadmapFields {
  initiative: string | null;
  proposed_by: string | null;
  project_type: string | null;
  category: string | null;
  criticality: string | null;
  process: string | null;
  benefits: string | null;
  change_management: string | null;
}

export interface Project extends RoadmapFields {
  id: number;
  name: string;
  description: string | null;
  area_id: number;
  status: string;
  owner_id: number | null;
  start_date: string | null;
  due_date: string | null;
  progress: number;
  created_at: string;
  updated_at: string;
  area_name: string | null;
  owner_name: string | null;
  is_mine: boolean;
  is_development: boolean;
  parent_id: number | null;
  parent_name: string | null;
  requirements: string | null;
}

export interface ProjectCreate {
  name: string;
  area_id: number;
  status?: ProjectStatus;
  description?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  progress?: number;
  category?: string | null;
  process?: string | null;
  project_type?: string | null;
  is_development?: boolean;
  parent_id?: number | null;
}

export interface ProjectUpdate extends Partial<RoadmapFields> {
  name?: string;
  status?: ProjectStatus;
  description?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  owner_id?: number | null;
  progress?: number;
  is_development?: boolean;
  parent_id?: number | null;
  requirements?: string | null;
}

export interface ProjectMember {
  user_id: number;
  name: string;
  email: string;
  role: string;
}

export const listProjects = () => api.get<Project[]>("/api/projects");
export const getProject = (id: number) => api.get<Project>(`/api/projects/${id}`);
export const createProject = (payload: ProjectCreate) => api.post<Project>("/api/projects", payload);
export const updateProject = (id: number, payload: ProjectUpdate) =>
  api.patch<Project>(`/api/projects/${id}`, payload);
export const deleteProject = (id: number) => api.del<void>(`/api/projects/${id}`);
export const listMembers = (id: number) => api.get<ProjectMember[]>(`/api/projects/${id}/members`);
export const addMember = (id: number, userId: number, role: string) =>
  api.post<ProjectMember[]>(`/api/projects/${id}/members`, { user_id: userId, role });
export const removeMember = (id: number, userId: number) =>
  api.del<ProjectMember[]>(`/api/projects/${id}/members/${userId}`);
