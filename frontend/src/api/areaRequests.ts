import { api } from "./client";

export interface AreaCatalogItem {
  id: number;
  name: string;
  description: string | null;
  member_count: number;
  leads: string[];
  is_member: boolean;
  pending: boolean;
}

export interface AreaRequest {
  id: number;
  kind: "join" | "new_area";
  status: "pending" | "approved" | "rejected";
  area_id: number | null;
  area_name: string | null;
  proposed_name: string | null;
  proposed_description: string | null;
  requester_id: number;
  requester_name: string | null;
  requester_email: string | null;
  note: string | null;
  created_at: string;
  decided_at: string | null;
}

export const areaCatalog = () => api.get<AreaCatalogItem[]>("/api/areas/catalog");
export const requestJoinArea = (areaId: number) =>
  api.post<AreaRequest>(`/api/areas/${areaId}/join`, {});
export const requestNewArea = (name: string, description?: string) =>
  api.post<AreaRequest>("/api/area-requests/new-area", { name, description: description || null });
export const myAreaRequests = () => api.get<AreaRequest[]>("/api/area-requests/mine");
export const pendingAreaRequests = () => api.get<AreaRequest[]>("/api/area-requests/pending");
export const approveAreaRequest = (id: number) =>
  api.post<AreaRequest>(`/api/area-requests/${id}/approve`, {});
export const rejectAreaRequest = (id: number, note?: string) =>
  api.post<AreaRequest>(`/api/area-requests/${id}/reject`, { note: note || null });
