import type { ActivityProject, ActivityTask } from "./admin";
import { api } from "./client";
import type { TaskSummary } from "./tasks";

export interface AreaLite {
  id: number;
  name: string;
  slug: string;
}

export interface AreaAdminScope {
  areas: AreaLite[];
}

export interface AreaAdminStats {
  areas: number;
  projects: number;
  active_projects: number;
  tasks: number;
  open_tasks: number;
  overdue_tasks: number;
  members: number;
}

export interface AreaAdminActivity {
  recent_projects: ActivityProject[];
  recent_tasks: ActivityTask[];
}

export interface AreaMemberRow {
  user_id: number;
  name: string;
  email: string;
  area_id: number;
  area_name: string;
  area_role: string;
}

export interface AreaAdminMembers {
  members: AreaMemberRow[];
}

export const getAreaAdminScope = () => api.get<AreaAdminScope>("/api/area-admin/scope");
export const getAreaAdminStats = () => api.get<AreaAdminStats>("/api/area-admin/stats");
export const getAreaAdminActivity = (limit = 12) =>
  api.get<AreaAdminActivity>(`/api/area-admin/activity?limit=${limit}`);
export const getAreaAdminTasks = () => api.get<TaskSummary>("/api/area-admin/tasks");
export const getAreaAdminMembers = () => api.get<AreaAdminMembers>("/api/area-admin/members");
export const setAreaMember = (areaId: number, userId: number, areaRole: string) =>
  api.put<void>(`/api/area-admin/areas/${areaId}/members`, {
    user_id: userId,
    area_role: areaRole,
  });
export const removeAreaMember = (areaId: number, userId: number) =>
  api.del<void>(`/api/area-admin/areas/${areaId}/members/${userId}`);
