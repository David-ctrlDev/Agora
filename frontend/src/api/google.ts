import { api } from "./client";

export interface GoogleStatus {
  connected: boolean;
  scopes: string | null;
}

export interface GoogleDocument {
  id: number;
  project_id: number;
  source: string;
  external_id: string;
  title: string;
  kind: string | null;
  web_url: string | null;
  occurred_at: string | null;
}

export const googleStatus = () => api.get<GoogleStatus>("/api/google/status");
export const googleConnect = () => api.post<GoogleStatus>("/api/google/connect", {});
export const googleDisconnect = () => api.post<GoogleStatus>("/api/google/disconnect", {});
export const syncGoogle = (projectId: number) =>
  api.post<{ new_documents: number }>(`/api/projects/${projectId}/google/sync`, {});
export const listGoogleDocuments = (projectId: number) =>
  api.get<GoogleDocument[]>(`/api/projects/${projectId}/google/documents`);
