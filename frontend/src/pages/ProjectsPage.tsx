import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, List, Plus, Search } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { listAreas } from "../api/areas";
import {
  PROJECT_STATUS,
  type Project,
  type ProjectStatus,
  createProject,
  listProjects,
} from "../api/projects";
import { Badge, Button, Card, Input, PageHeader, Select, Spinner } from "../components/ui";

const STATUS_ACCENT: Record<string, string> = {
  planned: "#94a3b8",
  active: "#6366f1",
  on_hold: "#f59e0b",
  done: "#10b981",
  archived: "#cbd5e1",
};
const VIEW_KEY = "agora-projects-view";

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const areasQuery = useQuery({ queryKey: ["areas"], queryFn: listAreas });

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [areaId, setAreaId] = useState<number | "">("");
  const [status, setStatus] = useState<ProjectStatus>("planned");
  const [dueDate, setDueDate] = useState("");
  const [description, setDescription] = useState("");

  const [search, setSearch] = useState("");
  const [areaFilter, setAreaFilter] = useState<number | "">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [view, setView] = useState<"cards" | "list">(
    () => (localStorage.getItem(VIEW_KEY) as "cards" | "list") || "cards",
  );
  const chooseView = (v: "cards" | "list") => {
    setView(v);
    localStorage.setItem(VIEW_KEY, v);
  };

  const create = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setName("");
      setAreaId("");
      setStatus("planned");
      setDueDate("");
      setDescription("");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || areaId === "") return;
    create.mutate({
      name: name.trim(),
      area_id: Number(areaId),
      status,
      due_date: dueDate || null,
      description: description.trim() || null,
    });
  };

  const areas = areasQuery.data ?? [];
  const projects = projectsQuery.data ?? [];

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return projects.filter(
      (p) =>
        (!q ||
          p.name.toLowerCase().includes(q) ||
          (p.description ?? "").toLowerCase().includes(q)) &&
        (areaFilter === "" || p.area_id === areaFilter) &&
        (!statusFilter || p.status === statusFilter),
    );
  }, [projects, search, areaFilter, statusFilter]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Proyectos"
        description="Proyectos de tus áreas."
        actions={
          areas.length > 0 ? (
            <Button onClick={() => setShowForm((v) => !v)} variant={showForm ? "secondary" : "primary"}>
              <Plus className="h-4 w-4" /> Nuevo proyecto
            </Button>
          ) : null
        }
      />

      {showForm && (
        <Card className="p-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nombre del proyecto"
                maxLength={200}
              />
              <Select
                label="Área"
                value={areaId}
                onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Selecciona un área</option>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
              <Select label="Estado" value={status} onChange={(e) => setStatus(e.target.value as ProjectStatus)}>
                {Object.entries(PROJECT_STATUS).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value.label}
                  </option>
                ))}
              </Select>
              <Input
                label="Fecha de entrega"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            <Input
              label="Descripción (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descripción"
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={!name.trim() || areaId === "" || create.isPending}>
                {create.isPending ? "Creando…" : "Crear proyecto"}
              </Button>
            </div>
            {create.isError && <p className="text-sm text-red-600">{(create.error as Error).message}</p>}
          </form>
        </Card>
      )}

      {/* Barra de filtros + toggle de vista */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre o descripción…"
            className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
        <div className="sm:w-44">
          <Select value={areaFilter} onChange={(e) => setAreaFilter(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Todas las áreas</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </div>
        <div className="sm:w-44">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Todos los estados</option>
            {Object.entries(PROJECT_STATUS).map(([key, value]) => (
              <option key={key} value={key}>
                {value.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex h-10 shrink-0 overflow-hidden rounded-lg border border-slate-300">
          <button
            type="button"
            onClick={() => chooseView("cards")}
            title="Tarjetas"
            className={`flex w-10 items-center justify-center transition ${view === "cards" ? "bg-brand-600 text-white" : "bg-white text-slate-500 hover:bg-slate-50"}`}
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => chooseView("list")}
            title="Lista"
            className={`flex w-10 items-center justify-center border-l border-slate-300 transition ${view === "list" ? "bg-brand-600 text-white" : "bg-white text-slate-500 hover:bg-slate-50"}`}
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {projectsQuery.isLoading ? (
        <Spinner label="Cargando proyectos…" />
      ) : projects.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-500">No hay proyectos todavía.</Card>
      ) : (
        <>
          <p className="text-xs text-slate-500">
            {filtered.length} de {projects.length} proyectos
          </p>

          {filtered.length === 0 ? (
            <Card className="p-8 text-center text-sm text-slate-500">
              Ningún proyecto coincide con los filtros.
            </Card>
          ) : view === "cards" ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((p: Project) => {
                const st = PROJECT_STATUS[p.status] ?? { label: p.status, tone: "neutral" as const };
                return (
                  <Link key={p.id} to={`/proyectos/${p.id}`}>
                    <Card className="group h-full overflow-hidden p-0 transition hover:-translate-y-0.5 hover:shadow-md">
                      <div className="h-1" style={{ background: STATUS_ACCENT[p.status] ?? "#cbd5e1" }} />
                      <div className="p-5">
                        <div className="mb-2 flex items-start justify-between gap-2">
                          <h3 className="font-semibold leading-snug text-slate-900">{p.name}</h3>
                          <Badge tone={st.tone}>{st.label}</Badge>
                        </div>
                        {p.description && (
                          <p className="mb-3 line-clamp-2 text-sm text-slate-500">{p.description}</p>
                        )}
                        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                          <Badge tone="neutral">{p.area_name}</Badge>
                          {p.owner_name && <span>· {p.owner_name}</span>}
                          {p.due_date && (
                            <span>· vence {new Date(p.due_date).toLocaleDateString("es-CO")}</span>
                          )}
                        </div>
                      </div>
                    </Card>
                  </Link>
                );
              })}
            </div>
          ) : (
            <Card className="divide-y divide-slate-100 overflow-hidden">
              {filtered.map((p: Project) => {
                const st = PROJECT_STATUS[p.status] ?? { label: p.status, tone: "neutral" as const };
                return (
                  <Link
                    key={p.id}
                    to={`/proyectos/${p.id}`}
                    className="flex items-center gap-3 px-4 py-3 transition hover:bg-slate-50"
                  >
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ background: STATUS_ACCENT[p.status] ?? "#cbd5e1" }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-slate-900">{p.name}</div>
                      <div className="truncate text-xs text-slate-400">
                        {p.area_name}
                        {p.owner_name && ` · ${p.owner_name}`}
                      </div>
                    </div>
                    {p.due_date && (
                      <span className="hidden shrink-0 text-xs text-slate-400 sm:block">
                        {new Date(p.due_date).toLocaleDateString("es-CO")}
                      </span>
                    )}
                    <Badge tone={st.tone}>{st.label}</Badge>
                  </Link>
                );
              })}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
