import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, ChevronsUpDown, LayoutGrid, List, Plus, Search, X } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { listAreas } from "../api/areas";
import { listCatalog } from "../api/catalog";
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
  const catProcess = useQuery({ queryKey: ["catalog", "process"], queryFn: () => listCatalog("process") });
  const catCategory = useQuery({ queryKey: ["catalog", "category"], queryFn: () => listCatalog("category") });
  const catType = useQuery({ queryKey: ["catalog", "project_type"], queryFn: () => listCatalog("project_type") });

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [areaId, setAreaId] = useState<number | "">("");
  const [status, setStatus] = useState<ProjectStatus>("planned");
  const [startDate, setStartDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [processName, setProcessName] = useState("");
  const [projectType, setProjectType] = useState("");

  const [scope, setScope] = useState<"mine" | "area">("mine");
  const [search, setSearch] = useState("");
  const [areaFilter, setAreaFilter] = useState<number | "">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
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
      setCategory("");
      setProcessName("");
      setProjectType("");
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
      category: category || null,
      process: processName || null,
      project_type: projectType || null,
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
        (scope === "area" || p.is_mine) &&
        (!q ||
          p.name.toLowerCase().includes(q) ||
          (p.description ?? "").toLowerCase().includes(q)) &&
        (areaFilter === "" || p.area_id === areaFilter) &&
        (!statusFilter || p.status === statusFilter) &&
        (!ownerFilter || p.owner_name === ownerFilter) &&
        (!dateFrom || (p.due_date != null && p.due_date >= dateFrom)) &&
        (!dateTo || (p.due_date != null && p.due_date <= dateTo)),
    );
  }, [projects, scope, search, areaFilter, statusFilter, ownerFilter, dateFrom, dateTo]);

  type SortKey =
    | "name"
    | "status"
    | "progress"
    | "start_date"
    | "due_date"
    | "owner_name"
    | "category"
    | "criticality"
    | "project_type"
    | "process";
  const SORT_COLUMNS: { key: SortKey; label: string }[] = [
    { key: "name", label: "Proyecto" },
    { key: "status", label: "Estado" },
    { key: "progress", label: "Avance" },
    { key: "start_date", label: "Inicio" },
    { key: "due_date", label: "Entrega" },
    { key: "owner_name", label: "Líder" },
    { key: "category", label: "Categoría" },
    { key: "criticality", label: "Criticidad" },
    { key: "project_type", label: "Tipo" },
    { key: "process", label: "Proceso" },
  ];
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  };
  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const key = sortKey;
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const va = a[key];
      const vb = b[key];
      const na = va == null || va === "";
      const nb = vb == null || vb === "";
      if (na && nb) return 0;
      if (na) return 1; // nulos siempre al final
      if (nb) return -1;
      if (key === "progress") return ((va as number) - (vb as number)) * dir;
      return String(va).localeCompare(String(vb), "es", { numeric: true }) * dir;
    });
  }, [filtered, sortKey, sortDir]);

  const mineCount = useMemo(() => projects.filter((p) => p.is_mine).length, [projects]);

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
            <div className="grid gap-4 sm:grid-cols-3">
              <Select label="Proceso" value={processName} onChange={(e) => setProcessName(e.target.value)}>
                <option value="">— Sin proceso —</option>
                {(catProcess.data ?? []).map((t) => (
                  <option key={t.id} value={t.name}>{t.name}</option>
                ))}
              </Select>
              <Select label="Categoría" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">— Sin categoría —</option>
                {(catCategory.data ?? []).map((t) => (
                  <option key={t.id} value={t.name}>{t.name}</option>
                ))}
              </Select>
              <Select label="Tipo" value={projectType} onChange={(e) => setProjectType(e.target.value)}>
                <option value="">— Sin tipo —</option>
                {(catType.data ?? []).map((t) => (
                  <option key={t.id} value={t.name}>{t.name}</option>
                ))}
              </Select>
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

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-10 shrink-0 overflow-hidden rounded-lg border border-slate-300 text-sm font-medium">
          <button
            type="button"
            onClick={() => setScope("mine")}
            className={`px-3 transition ${scope === "mine" ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
          >
            Míos{mineCount ? ` (${mineCount})` : ""}
          </button>
          <button
            type="button"
            onClick={() => setScope("area")}
            className={`border-l border-slate-300 px-3 transition ${scope === "area" ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
          >
            Del área
          </button>
        </div>
        <div className="relative min-w-[220px] flex-1">
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
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className="hidden sm:inline">Entrega</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            title="Entrega desde"
            className="h-10 rounded-xl border border-slate-300 bg-white px-2.5 text-sm text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
          <span>–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            title="Entrega hasta"
            className="h-10 rounded-xl border border-slate-300 bg-white px-2.5 text-sm text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
          {(dateFrom || dateTo) && (
            <button
              type="button"
              onClick={() => {
                setDateFrom("");
                setDateTo("");
              }}
              title="Limpiar fechas"
              className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
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
              <div className="max-h-[70vh] overflow-auto">
                <table className="w-full min-w-[1080px] text-sm">
                  <thead className="sticky top-0 z-10">
                    <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {SORT_COLUMNS.map((col) => {
                        const active = sortKey === col.key;
                        return (
                          <th key={col.key} className="px-3 py-2.5">
                            <button
                              type="button"
                              onClick={() => toggleSort(col.key)}
                              title={`Ordenar por ${col.label}`}
                              className={`inline-flex items-center gap-1 uppercase tracking-wide transition hover:text-slate-700 ${active ? "text-slate-800" : ""}`}
                            >
                              {col.label}
                              {active ? (
                                sortDir === "asc" ? (
                                  <ChevronUp className="h-3 w-3" />
                                ) : (
                                  <ChevronDown className="h-3 w-3" />
                                )
                              ) : (
                                <ChevronsUpDown className="h-3 w-3 text-slate-300" />
                              )}
                            </button>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sorted.map((p: Project) => {
                      const st = PROJECT_STATUS[p.status] ?? { label: p.status, tone: "neutral" as const };
                      const crit = (p.criticality ?? "").toUpperCase();
                      const overdue =
                        p.due_date != null && new Date(p.due_date) < new Date() && p.status !== "done";
                      return (
                        <tr
                          key={p.id}
                          onClick={() => navigate(`/proyectos/${p.id}`)}
                          className="cursor-pointer transition hover:bg-slate-50"
                        >
                          <td className="px-3 py-2.5">
                            <div className="flex items-center gap-2">
                              <span
                                className="h-2 w-2 shrink-0 rounded-full"
                                style={{ background: STATUS_ACCENT[p.status] ?? "#cbd5e1" }}
                              />
                              <div className="min-w-0">
                                <div className="max-w-[260px] truncate font-medium text-slate-900" title={p.name}>
                                  {p.name}
                                </div>
                                {p.initiative && (
                                  <div className="text-[11px] uppercase tracking-wide text-slate-400">
                                    {p.initiative}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-2.5">
                            <Badge tone={st.tone}>{st.label}</Badge>
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 w-20 rounded-full bg-slate-100">
                                <div
                                  className="h-1.5 rounded-full bg-brand-500"
                                  style={{ width: `${p.progress}%` }}
                                />
                              </div>
                              <span className="w-8 text-right tabular-nums text-xs text-slate-500">
                                {p.progress}%
                              </span>
                            </div>
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-500">
                            {fmtDate(p.start_date)}
                          </td>
                          <td
                            className={`whitespace-nowrap px-3 py-2.5 text-xs ${overdue ? "font-semibold text-red-600" : "text-slate-500"}`}
                          >
                            {fmtDate(p.due_date)}
                          </td>
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.owner_name)}</td>
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
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.project_type)}</td>
                          <td className="px-3 py-2.5 text-slate-500">{dash(p.process)}</td>
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
