import { api } from "./client";

export interface AreaMembership {
  id: number;
  name: string;
  slug: string;
  area_role: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  name: string;
  role: string;
  avatar_url: string | null;
  areas: AreaMembership[];
}

export interface DevUser {
  id: number;
  email: string;
  name: string;
  role: string;
  areas: string[];
}

export const googleLoginUrl = "/api/auth/login/google";

export const getMe = () => api.get<CurrentUser>("/api/auth/me");
export const listDevUsers = () => api.get<DevUser[]>("/api/auth/dev-users");
export const devLogin = (userId: number) =>
  api.post<CurrentUser>("/api/auth/dev-login", { user_id: userId });
export const logout = () => api.post<{ ok: boolean }>("/api/auth/logout", {});
