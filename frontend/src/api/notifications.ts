import { api } from "./client";

export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string;
  severity: string;
  status: string;
  area_id: number | null;
  project_id: number | null;
  created_at: string;
}

export const listNotifications = () => api.get<Notification[]>("/api/notifications");
export const unreadCount = () => api.get<{ count: number }>("/api/notifications/unread-count");
export const markRead = (id: number) => api.post<Notification>(`/api/notifications/${id}/read`, {});
export const markAllRead = () => api.post<{ ok: boolean }>("/api/notifications/read-all", {});
export const runDetection = () => api.post<{ created: number }>("/api/notifications/run", {});
