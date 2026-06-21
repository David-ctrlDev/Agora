import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, List, Plus, Search } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

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
  active: "#10b981",
  on_hold: "#f59e0b",
  done: "#047857",
  archived: "#cbd5e1",
};
const VIEW_KEY = "agora-projects-view";
const CRIT_STYLE: Record<string, string> = {
  ALTA: "bg-red-100 text-red-700",
  MEDIA: "bg-amber-100 text-amber-700",
  BAJA: "bg-slate-100 text-slate-600",
};

function fmtDate(d: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "2-digit" });
}
const dash = (v: string | null | undefined) => (v && v.trim() ? v : "—");

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const areasQuery = useQuery({ queryKey: ["areas"], queryFn: listAreas });

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [areaId, setAreaId] = useState<number | "">("");
  const [status, setStatus] = useState<ProjectStatus>("planned");
  const [startDate, setStartDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [description, setDescription] = useState("");

  const [search, setSearch] = useState("");
  const [areaFilter, setAreaFilter] = useState<number | "">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
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
      setStartDate("");
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
      start_date: startDate || null,
      due_date: dueDate || null,
      description: description.trim() || null,
    });
  };

  const areas = areasQuery.data ?? [];
  const projects = projectsQuery.data ?? [];

  const owners = useMemo(
    () => [...new Set(projects.map((p) => p.owner_name).filter((n): n is string => !!n))].sort(),
    [projects],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return projects.filter(
      (p) =>
        (!q ||
          p.name.toLowerCase().includes(q) ||
          (p.description ?? "").toLowerCase().includes(q)) &&
        (areaFilter === "" || p.area_id === areaFilter) &&
        (!statusFilter || p.status === statusFilter) &&
        (!ownerFilter || p.owner_name === ownerFilter),
    );
  }, [projects, search, areaFilter, statusFilter, ownerFilter]);

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
              <div className="grid grid-cols-2 gap-3">
                <Input label="Inicio" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <Input label="Entrega" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>
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
        <div className="sm:w-48">
          <Select value={ownerFilter} onChange={(e) => setOwnerFilter(e.target.value)}>
            <option value="">Todos los responsables</option>
            {owners.map((o) => (
              <option key={o} value={o}>
                {o}
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
                        <div className="mb-3">
                          <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                            <span>Avance</span>
                            <span className="tabular-nums">{p.progress}%</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-slate-100">
                            <div className="h-1.5 rounded-full bg-brand-500" style={{ width: `${p.progress}%` }} />
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
                          <Badge tone="neutral">{p.area_name}</Badge>
                          {p.owner_name && <span>· {p.owner_name}</span>}
                          <span className="w-full">📅 {fmtDate(p.start_date)} → {fmtDate(p.due_date)}</span>
                        </div>
                      </div>
                    </Card>
                  </Link>
                );
              })}
            </div>
          ) : (
            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px] text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <th className="px-3 py-2.5">Iniciativa</th>
                      <th className="px-3 py-2.5">Proyecto</th>
                      <th className="px-3 py-2.5">Tipo</th>
                      <th className="px-3 py-2.5">Categoría</th>
                      <th className="px-3 py-2.5">Criticidad</th>
                      <th className="px-3 py-2.5">Proceso</th>
                      <th className="px-3 py-2.5">Líder</th>
                      <th className="px-3 py-2.5">Estado</th>
                      <th className="px-3 py-2.5 text-right">Avance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filtered.map((p: Project) => {
                      const st = PROJECT_STATUS[p.status] ?? { label: p.status, tone: "neutral" as const };
                      const crit = (p.criticality ?? "").toUpperCase();
                      return (
                        <tr
                          key={p.id}
                          onClick={() => navigate(`/proyectos/${p.id}`)}
                          className="cursor-pointer transition hover:bg-slate-50"
                        >
                          <td className="px-3 py-2.5">
                            {p.initiative ? (
                              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600">
                                {p.initiative}
                              </span>
                            ) : (
                              <span className="text-slate-300">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="flex items-center gap-2">
                              <span
                                className="h-2 w-2 shrink-0 rounded-full"
                                style={{ background: STATUS_ACCENT[p.status] ?? "#cbd5e1" }}
                              />
                              <span
                                className="block max-w-[280px] truncate font-medium text-slate-900"
                                title={p.name}
                              >
                                {p.name}
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.project_type)}</td>
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.category)}</td>
                          <td className="px-3 py-2.5">
                            {crit ? (
                              <span
                                className={`rounded-full px-2 py-0.5 text-xs font-medium ${CRIT_STYLE[crit] ?? "bg-slate-100 text-slate-600"}`}
                              >
                                {crit}
                              </span>
                            ) : (
                              <span className="text-slate-300">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.process)}</td>
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.owner_name)}</td>
                          <td className="px-3 py-2.5">
                            <Badge tone={st.tone}>{st.label}</Badge>
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="flex items-center justify-end gap-2">
                              <div className="h-1.5 w-16 rounded-full bg-slate-100">
                                <div
                                  className="h-1.5 rounded-full bg-brand-500"
                                  style={{ width: `${p.progress}%` }}
                                />
                              </div>
                              <span className="w-9 text-right tabular-nums text-xs text-slate-500">
                                {p.progress}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
