import { api } from "./client";

export type TaskStatus = "todo" | "in_progress" | "blocked" | "done";
export type TaskPriority = "low" | "medium" | "high";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

export const TASK_STATUS: Record<string, { label: string; tone: Tone }> = {
  todo: { label: "Por hacer", tone: "neutral" },
  in_progress: { label: "En progreso", tone: "brand" },
  blocked: { label: "Bloqueada", tone: "danger" },
  done: { label: "Hecha", tone: "success" },
};

export const TASK_STATUS_ORDER = ["todo", "in_progress", "blocked", "done"] as const;

export const TASK_PRIORITY: Record<string, { label: string; tone: Tone }> = {
  low: { label: "Baja", tone: "neutral" },
  medium: { label: "Media", tone: "warning" },
  high: { label: "Alta", tone: "danger" },
};

export interface Task {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assignee_id: number | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  assignee_name: string | null;
  project_name: string | null;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: number | null;
  due_date?: string | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: number | null;
  due_date?: string | null;
}

export const listProjectTasks = (projectId: number) =>
  api.get<Task[]>(`/api/projects/${projectId}/tasks`);
export const createTask = (projectId: number, payload: TaskCreate) =>
  api.post<Task>(`/api/projects/${projectId}/tasks`, payload);
export const updateTask = (taskId: number, payload: TaskUpdate) =>
  api.patch<Task>(`/api/tasks/${taskId}`, payload);
export const deleteTask = (taskId: number) => api.del<void>(`/api/tasks/${taskId}`);
export const listMyTasks = () => api.get<Task[]>("/api/tasks/mine");
