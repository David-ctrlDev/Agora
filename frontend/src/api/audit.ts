import { api } from "./client";

export interface AuditEntry {
  id: number;
  entity_type: string;
  entity_id: number | null;
  action: string;
  summary: string;
  actor_name: string | null;
  created_at: string;
}

export const getAudit = (projectId: number) =>
  api.get<AuditEntry[]>(`/api/projects/${projectId}/audit`);
