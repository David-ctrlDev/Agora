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

export const listAdminUsers = () => api.get<AdminUser[]>("/api/admin/users");
export const createAdminUser = (payload: {
  email: string;
  name: string;
  role: string;
  area_ids: number[];
}) => api.post<AdminUser>("/api/admin/users", payload);
export const updateAdminUser = (
  id: number,
  payload: { name?: string; role?: string; is_active?: boolean },
) => api.patch<AdminUser>(`/api/admin/users/${id}`, payload);
export const setUserAreas = (
  id: number,
  areas: { area_id: number; area_role: string }[],
) => api.put<AdminUser>(`/api/admin/users/${id}/areas`, { areas });

export const listAdminAreas = () => api.get<AdminArea[]>("/api/admin/areas");
export const createAdminArea = (payload: { name: string; description?: string | null }) =>
  api.post<AdminArea>("/api/admin/areas", payload);
export const updateAdminArea = (
  id: number,
  payload: { name?: string; description?: string | null; is_active?: boolean },
) => api.patch<AdminArea>(`/api/admin/areas/${id}`, payload);
