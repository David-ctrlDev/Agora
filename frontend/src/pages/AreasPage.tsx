import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, FolderKanban, Plus } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { createArea, listAreas } from "../api/areas";
import { PROJECT_STATUS, listProjects } from "../api/projects";
import { useMe } from "../auth/useAuth";
import AreaCatalog from "../components/AreaCatalog";
import { Badge, Button, Card, Input, PageHeader, Spinner } from "../components/ui";

export default function AreasPage() {
  const queryClient = useQueryClient();
  const me = useMe();
  const isAdmin = me.data?.role === "admin";

  const areasQuery = useQuery({ queryKey: ["areas"], queryFn: listAreas });
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const create = useMutation({
    mutationFn: createArea,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["areas"] });
      setName("");
      setDescription("");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate({ name: trimmed, description: description.trim() || null });
  };

  const areas = areasQuery.data ?? [];
  const projects = projectsQuery.data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Áreas"
        description={
          isAdmin
            ? "Departamentos de Invesa. Despliega un área para ver sus proyectos."
            : "Áreas a las que perteneces. Despliega para ver sus proyectos."
        }
      />

      {isAdmin && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Nueva área</h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <Input
              label="Nombre"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="p. ej. Recursos Humanos"
              maxLength={120}
            />
            <Input
              label="Descripción (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descripción"
            />
            <Button type="submit" disabled={!name.trim() || create.isPending} className="shrink-0">
              <Plus className="h-4 w-4" />
              {create.isPending ? "Creando…" : "Crear área"}
            </Button>
          </form>
          {create.isError && (
            <p className="mt-3 text-sm text-red-600">{(create.error as Error).message}</p>
          )}
        </Card>
      )}

      <section className="space-y-3">
        {areasQuery.isLoading && <Spinner label="Cargando áreas…" />}
        {areasQuery.isError && (
          <p className="text-sm text-red-600">No se pudieron cargar las áreas.</p>
        )}
        {areas.length === 0 && !areasQuery.isLoading && (
          <Card className="p-8 text-center text-sm text-slate-500">
            {isAdmin
              ? "Aún no hay áreas. Crea la primera arriba."
              : "No perteneces a ningún área todavía."}
          </Card>
        )}

        {areas.map((area) => {
          const areaProjects = projects.filter((p) => p.area_id === area.id);
          const isOpen = expanded === area.id;
          return (
            <Card key={area.id} className="overflow-hidden">
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : area.id)}
                className="flex w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-slate-50"
              >
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">{area.name}</span>
                    <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                      {area.slug}
                    </code>
                    {!area.is_active && <Badge tone="neutral">Inactiva</Badge>}
                  </div>
                  {area.description && (
                    <div className="mt-0.5 text-xs text-slate-500">{area.description}</div>
                  )}
                </div>
                <span className="flex shrink-0 items-center gap-1.5 text-sm text-slate-500">
                  <FolderKanban className="h-4 w-4" /> {areaProjects.length}
                </span>
              </button>

              {isOpen && (
                <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-3">
                  {areaProjects.length === 0 ? (
                    <p className="text-sm text-slate-400">Esta área no tiene proyectos todavía.</p>
                  ) : (
                    <ul className="divide-y divide-slate-100">
                      {areaProjects.map((p) => {
                        const st = PROJECT_STATUS[p.status] ?? {
                          label: p.status,
                          tone: "neutral" as const,
                        };
                        return (
                          <li key={p.id}>
                            <Link
                              to={`/proyectos/${p.id}`}
                              className="flex items-center justify-between gap-3 py-2 text-sm transition hover:text-brand-700"
                            >
                              <span className="truncate font-medium text-slate-800">{p.name}</span>
                              <Badge tone={st.tone}>{st.label}</Badge>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </section>

      <AreaCatalog />
    </div>
  );
}
