import { api } from "./client";

export interface KnowledgeDocument {
  id: number;
  project_id: number;
  title: string;
  source: string;
  created_at: string;
}

export const listDocuments = (projectId: number) =>
  api.get<KnowledgeDocument[]>(`/api/projects/${projectId}/documents`);
export const createDocument = (projectId: number, title: string, content: string) =>
  api.post<KnowledgeDocument>(`/api/projects/${projectId}/documents`, { title, content });
export const deleteDocument = (documentId: number) =>
  api.del<void>(`/api/documents/${documentId}`);
