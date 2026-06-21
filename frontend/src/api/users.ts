import { api } from "./client";

export interface AppUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

export const listUsers = () => api.get<AppUser[]>("/api/users");
