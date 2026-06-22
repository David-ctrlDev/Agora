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
  twofa_enabled: boolean;
}

export interface LoginResponse {
  needs_2fa: boolean;
  user: CurrentUser | null;
}

export interface TwoFactorSetup {
  secret: string;
  otpauth_uri: string;
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
  api.post<LoginResponse>("/api/auth/dev-login", { user_id: userId });
export const logout = () => api.post<{ ok: boolean }>("/api/auth/logout", {});

export const setup2fa = () => api.post<TwoFactorSetup>("/api/auth/2fa/setup", {});
export const enable2fa = (code: string) => api.post<CurrentUser>("/api/auth/2fa/enable", { code });
export const disable2fa = (code: string) => api.post<CurrentUser>("/api/auth/2fa/disable", { code });
export const verify2fa = (code: string) => api.post<CurrentUser>("/api/auth/2fa/verify", { code });
