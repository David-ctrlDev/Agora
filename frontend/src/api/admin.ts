import { api } from "./client";

export interface AdminAreaMembership {
  area_id: number;
  name: string;
  area_role: string;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  twofa_enabled: boolean;
  areas: AdminAreaMembership[];
}

export interface AdminArea {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminStats {
  users: number;
  active_users: number;
  admins: number;
  two_fa: number;
  areas: number;
  projects: number;
  active_projects: number;
  tasks: number;
  open_tasks: number;
  overdue_tasks: number;
  google_provider: string;
  gemini_provider: string;
}

export interface ActivityProject {
  id: number;
  name: string;
  status: string;
  area_name: string | null;
  owner_name: string | null;
  created_at: string;
}

export interface ActivityTask {
  id: number;
  title: string;
  status: string;
  priority: string;
  project_id: number;
  project_name: string | null;
  assignee_name: string | null;
  created_at: string;
}

export interface ActivityUser {
  id: number;
  name: string;
  email: string;
  role: string;
  at: string;
}

export interface AdminActivity {
  recent_projects: ActivityProject[];
  recent_tasks: ActivityTask[];
  recent_logins: ActivityUser[];
  recent_users: ActivityUser[];
}

export const getAdminStats = () => api.get<AdminStats>("/api/admin/stats");
export const getAdminActivity = (limit = 10) =>
  api.get<AdminActivity>(`/api/admin/activity?limit=${limit}`);
export const listAdminUsers = () => api.get<AdminUser[]>("/api/admin/users");
export const createAdminUser = (payload: {
  email: string;
  name: string;
  role: string;
  area_ids: number[];
}) => api.post<AdminUser>("/api/admin/users", payload);
export const updateAdminUser = (
  id: number,
  payload: { name?: string; email?: string; role?: string; is_active?: boolean },
) => api.patch<AdminUser>(`/api/admin/users/${id}`, payload);
export const setUserAreas = (
  id: number,
  areas: { area_id: number; area_role: string }[],
) => api.put<AdminUser>(`/api/admin/users/${id}/areas`, { areas });
export const resetUser2fa = (id: number) =>
  api.post<AdminUser>(`/api/admin/users/${id}/reset-2fa`, {});

export const listAdminAreas = () => api.get<AdminArea[]>("/api/admin/areas");
export const createAdminArea = (payload: { name: string; description?: string | null }) =>
  api.post<AdminArea>("/api/admin/areas", payload);
export const updateAdminArea = (
  id: number,
  payload: { name?: string; description?: string | null; is_active?: boolean },
) => api.patch<AdminArea>(`/api/admin/areas/${id}`, payload);
