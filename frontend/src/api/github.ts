import { api } from "./client";

export interface GitHubRepo {
  id: number;
  project_id: number;
  full_name: string;
  html_url: string | null;
  created_at: string;
}

export interface GitHubEvent {
  id: number;
  repo_id: number;
  event_type: string;
  title: string;
  author: string | null;
  html_url: string | null;
  occurred_at: string;
}

export const listRepos = (projectId: number) =>
  api.get<GitHubRepo[]>(`/api/projects/${projectId}/github/repos`);
export const linkRepo = (projectId: number, fullName: string) =>
  api.post<GitHubRepo>(`/api/projects/${projectId}/github/repos`, { full_name: fullName });
export const unlinkRepo = (repoId: number) => api.del<void>(`/api/github/repos/${repoId}`);
export const syncRepo = (repoId: number) =>
  api.post<{ new_events: number }>(`/api/github/repos/${repoId}/sync`, {});
export const listActivity = (projectId: number) =>
  api.get<GitHubEvent[]>(`/api/projects/${projectId}/github/activity`);
