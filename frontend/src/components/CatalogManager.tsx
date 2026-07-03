import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  type CatalogKind,
  CATALOG_KINDS,
  CATALOG_LABELS,
  createCatalogTerm,
  deleteCatalogTerm,
  listAdminCatalog,
} from "../api/catalog";
import { Button, Card, Input, Spinner } from "./ui";

function errMsg(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return detail ?? "No se pudo guardar.";
}

/** Gestión de las maestras (proceso, categoría, tipo): agregar y eliminar valores. */
export function CatalogManager() {
  const qc = useQueryClient();
  const [kind, setKind] = useState<CatalogKind>("process");
  const [name, setName] = useState("");

  const q = useQuery({ queryKey: ["admin-catalog", kind], queryFn: () => listAdminCatalog(kind) });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-catalog", kind] });

  const create = useMutation({
    mutationFn: () => createCatalogTerm(kind, name.trim()),
    onSuccess: () => {
      invalidate();
      setName("");
    },
  });
  const del = useMutation({ mutationFn: (id: number) => deleteCatalogTerm(id), onSuccess: invalidate });

  const terms = q.data ?? [];

  return (
    <div className="space-y-4">
      <div className="inline-flex overflow-hidden rounded-xl border border-slate-300">
        {CATALOG_KINDS.map((k, i) => (
          <button
            key={k}
            type="button"
            onClick={() => {
              setKind(k);
              setName("");
            }}
            className={`px-3.5 py-1.5 text-sm font-medium transition ${i > 0 ? "border-l border-slate-300" : ""} ${
              kind === k ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            {CATALOG_LABELS[k]}
          </button>
        ))}
      </div>

      <Card className="p-5">
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (name.trim()) create.mutate();
          }}
          className="flex flex-wrap items-end gap-3"
        >
          <div className="min-w-[240px] flex-1">
            <Input
              label={`Nuevo valor en ${CATALOG_LABELS[kind]}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="p. ej. Producción"
            />
          </div>
          <Button type="submit" disabled={!name.trim() || create.isPending}>
            <Plus className="h-4 w-4" /> {create.isPending ? "Agregando…" : "Agregar"}
          </Button>
        </form>
        {create.isError && <p className="mt-2 text-sm text-rose-600">{errMsg(create.error)}</p>}
      </Card>

      {q.isLoading ? (
        <Spinner label="Cargando…" />
      ) : terms.length === 0 ? (
        <Card className="p-6 text-center text-sm text-slate-400">
          Aún no hay valores en {CATALOG_LABELS[kind]}.
        </Card>
      ) : (
        <Card className="divide-y divide-slate-100 overflow-hidden">
          {terms.map((t) => (
            <div key={t.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <span className="truncate text-sm font-medium text-slate-800">{t.name}</span>
              <button
                type="button"
                onClick={() => {
                  if (window.confirm(`¿Eliminar «${t.name}» de ${CATALOG_LABELS[kind]}?`)) del.mutate(t.id);
                }}
                className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50"
              >
                <Trash2 className="h-3.5 w-3.5" /> Eliminar
              </button>
            </div>
          ))}
        </Card>
      )}
      <p className="text-xs text-slate-400">
        Los valores no se duplican (se ignoran mayúsculas/acentos al comparar). Eliminar un valor lo
        quita de la lista para elegir; los proyectos que ya lo tenían conservan su texto.
      </p>
    </div>
  );
}
