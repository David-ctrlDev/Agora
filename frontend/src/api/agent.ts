import { api } from "./client";

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
}

export interface AgentAction {
  id: number;
  action_type: string;
  params: Record<string, unknown>;
  status: string;
  result: Record<string, unknown> | null;
  created_at: string;
}

export interface AgentMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
  action: AgentAction | null;
}

export interface Attachment {
  id: number;
  name: string;
  mime_type: string | null;
  source: string;
  char_count: number;
  created_at: string;
}

export const listConversations = () => api.get<Conversation[]>("/api/agent/conversations");
export const createConversation = () => api.post<Conversation>("/api/agent/conversations", {});
export const deleteConversation = (id: number) =>
  api.del<void>(`/api/agent/conversations/${id}`);
export const listMessages = (conversationId: number) =>
  api.get<AgentMessage[]>(`/api/agent/conversations/${conversationId}/messages`);
export const sendMessage = (
  conversationId: number,
  content: string,
  attachmentIds: number[] = [],
) =>
  api.post<AgentMessage>(`/api/agent/conversations/${conversationId}/messages`, {
    content,
    attachment_ids: attachmentIds,
  });

export const listAttachments = (conversationId: number) =>
  api.get<Attachment[]>(`/api/agent/conversations/${conversationId}/attachments`);
export const uploadAttachment = (conversationId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.upload<Attachment>(`/api/agent/conversations/${conversationId}/attachments`, form);
};
export const attachFromDrive = (conversationId: number, fileId: string) =>
  api.post<Attachment>(`/api/agent/conversations/${conversationId}/attachments/from-drive`, {
    file_id: fileId,
  });
export const deleteAttachment = (attachmentId: number) =>
  api.del<void>(`/api/agent/attachments/${attachmentId}`);
export const confirmAction = (actionId: number) =>
  api.post<AgentMessage>(`/api/agent/actions/${actionId}/confirm`, {});
export const cancelAction = (actionId: number) =>
  api.post<AgentMessage>(`/api/agent/actions/${actionId}/cancel`, {});
