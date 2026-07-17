import { api } from "./client";
import type { Task, TaskPriority } from "./tasks";

export interface TaskProposal {
  title: string;
  description: string;
  priority: TaskPriority;
}

/** Propone tareas desde el levantamiento (texto guardado + texto extra + adjunto opcional). */
export const proposeTasks = (projectId: number, file: File | null, extraText = "") => {
  const form = new FormData();
  if (file) form.append("file", file);
  form.append("extra_text", extraText);
  return api.upload<TaskProposal[]>(`/api/projects/${projectId}/requirements/proposals`, form);
};

export const acceptProposals = (projectId: number, tasks: TaskProposal[]) =>
  api.post<Task[]>(`/api/projects/${projectId}/requirements/accept`, { tasks });
