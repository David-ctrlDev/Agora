import { api } from "./client";

export interface KnowledgeDocument {
  id: number;
  project_id: number;
  title: string;
  source: string;
  file_name: string | null;
  mime_type: string | null;
  created_at: string;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  content_text: string | null;
}

export const listDocuments = (projectId: number) =>
  api.get<KnowledgeDocument[]>(`/api/projects/${projectId}/documents`);
export const getDocument = (documentId: number) =>
  api.get<KnowledgeDocumentDetail>(`/api/documents/${documentId}`);
export const createDocument = (
  projectId: number,
  title: string,
  content: string,
  source = "manual",
) => api.post<KnowledgeDocument>(`/api/projects/${projectId}/documents`, { title, content, source });
export const deleteDocument = (documentId: number) =>
  api.del<void>(`/api/documents/${documentId}`);
export const documentDownloadUrl = (documentId: number) =>
  `/api/documents/${documentId}/download`;

export async function uploadDocument(projectId: number, file: File, title?: string, source = "file") {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  form.append("source", source);
  const res = await fetch(`/api/projects/${projectId}/documents/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // sin cuerpo JSON
    }
    throw new Error(detail);
  }
  return (await res.json()) as KnowledgeDocument;
}

export interface DocumentVersion {
  id: number;
  document_id: number;
  version_no: number;
  title: string;
  source: string;
  file_name: string | null;
  mime_type: string | null;
  created_at: string;
}

export const listVersions = (documentId: number) =>
  api.get<DocumentVersion[]>(`/api/documents/${documentId}/versions`);
export const versionDownloadUrl = (versionId: number) =>
  `/api/document-versions/${versionId}/download`;

export async function addDocumentVersion(
  documentId: number,
  file?: File,
  content?: string,
  title?: string,
) {
  const form = new FormData();
  if (file) form.append("file", file);
  if (content) form.append("content", content);
  if (title) form.append("title", title);
  const res = await fetch(`/api/documents/${documentId}/versions`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // sin cuerpo JSON
    }
    throw new Error(detail);
  }
  return (await res.json()) as KnowledgeDocument;
}
