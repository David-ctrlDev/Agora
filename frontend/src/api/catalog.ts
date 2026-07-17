import { api } from "./client";

export type CatalogKind = "process" | "category" | "project_type" | "initiative";

export interface CatalogTerm {
  id: number;
  kind: string;
  name: string;
  is_active: boolean;
}

export const CATALOG_KINDS: CatalogKind[] = ["process", "category", "project_type", "initiative"];

export const CATALOG_LABELS: Record<CatalogKind, string> = {
  process: "Procesos",
  category: "Categorías",
  project_type: "Tipos de proyecto",
  initiative: "Iniciativas",
};

/** Valores activos de una maestra, para poblar selectores de formularios. */
export const listCatalog = (kind: CatalogKind) =>
  api.get<CatalogTerm[]>(`/api/catalog?kind=${kind}`);

// --- Administración de maestras ---
export const listAdminCatalog = (kind: CatalogKind) =>
  api.get<CatalogTerm[]>(`/api/admin/catalog?kind=${kind}`);
export const createCatalogTerm = (kind: CatalogKind, name: string) =>
  api.post<CatalogTerm>("/api/admin/catalog", { kind, name });
export const deleteCatalogTerm = (id: number) =>
  api.del<void>(`/api/admin/catalog/${id}`);
