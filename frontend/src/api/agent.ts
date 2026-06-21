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

export const listConversations = () => api.get<Conversation[]>("/api/agent/conversations");
export const createConversation = () => api.post<Conversation>("/api/agent/conversations", {});
export const deleteConversation = (id: number) =>
  api.del<void>(`/api/agent/conversations/${id}`);
export const listMessages = (conversationId: number) =>
  api.get<AgentMessage[]>(`/api/agent/conversations/${conversationId}/messages`);
export const sendMessage = (conversationId: number, content: string) =>
  api.post<AgentMessage>(`/api/agent/conversations/${conversationId}/messages`, { content });
export const confirmAction = (actionId: number) =>
  api.post<AgentMessage>(`/api/agent/actions/${actionId}/confirm`, {});
export const cancelAction = (actionId: number) =>
  api.post<AgentMessage>(`/api/agent/actions/${actionId}/cancel`, {});
