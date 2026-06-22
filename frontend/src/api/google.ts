import { api } from "./client";

export interface GoogleStatus {
  connected: boolean;
  scopes: string | null;
  provider?: string;
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

export interface DirectoryPerson {
  name: string;
  email: string;
}

export const getDirectory = () => api.get<DirectoryPerson[]>("/api/google/directory");

export interface DriveEntry {
  external_id: string;
  title: string;
  mime_type: string | null;
  web_url: string | null;
  modified_at: string | null;
  is_folder: boolean;
}

export const browseDrive = (folderId?: string | null, q?: string, shared?: boolean) => {
  const params = new URLSearchParams();
  if (folderId) params.set("folder_id", folderId);
  if (q && q.trim()) params.set("q", q.trim());
  if (shared) params.set("shared", "true");
  const qs = params.toString();
  return api.get<DriveEntry[]>(`/api/google/drive${qs ? `?${qs}` : ""}`);
};

export const importDriveFiles = (projectId: number, files: DriveEntry[]) =>
  api.post<{ new_documents: number; indexed: number }>(
    `/api/projects/${projectId}/google/import`,
    { files },
  );

export interface MeetingResult {
  title: string;
  meet_url: string | null;
  web_url: string;
  starts_at: string;
}

export const createMeeting = (
  projectId: number,
  payload: { title: string; attendees: string[]; when?: string | null },
) => api.post<MeetingResult>(`/api/projects/${projectId}/google/meetings`, payload);

export interface BusySlot {
  start: string;
  end: string;
}

export const freeBusy = (emails: string[], timeMin: string, timeMax: string) =>
  api.post<Record<string, BusySlot[]>>("/api/google/freebusy", {
    emails,
    time_min: timeMin,
    time_max: timeMax,
  });
