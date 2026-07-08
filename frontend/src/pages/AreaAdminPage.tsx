import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  FolderKanban,
  LayoutDashboard,
  ListChecks,
  Trash2,
  Users,
} from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import {
  getAreaAdminActivity,
  getAreaAdminMembers,
  getAreaAdminScope,
  getAreaAdminStats,
  getAreaAdminTasks,
  removeAreaMember,
  setAreaMember,
} from "../api/areaAdmin";
import { PROJECT_STATUS, type ProjectStatus } from "../api/projects";
import { TASK_STATUS } from "../api/tasks";
import { listUsers } from "../api/users";
import { useMe } from "../auth/useAuth";
import { TaskSummaryView } from "../components/TaskSummaryView";
import { Badge, Button, Card, Kpi, PageHeader, Panel, Select, Spinner } from "../components/ui";

function timeAgo(iso: string): string {
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return "hace un momento";
  const m = Math.floor(s / 60);
  if (m < 60) return `hace ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.floor(h / 24);
  if (d < 30) return `hace ${d} d`;
  const mo = Math.floor(d / 30);
  return `hace ${mo} ${mo === 1 ? "mes" : "meses"}`;
}

function ResumenTab() {
  const stats = useQuery({ queryKey: ["area-admin", "stats"], queryFn: getAreaAdminStats });
  const scope = useQuery({ queryKey: ["area-admin", "scope"], queryFn: getAreaAdminScope });
  if (stats.isLoading) return <Spinner label="Cargando…" />;
  const s = stats.data;
  if (!s) return null;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Áreas que administras" value={s.areas} icon={<Building2 className="h-4 w-4" />} tone="brand" />
        <Kpi label="Proyectos" value={s.projects} hint={`${s.active_projects} activos`} icon={<FolderKanban className="h-4 w-4" />} tone="emerald" />
        <Kpi label="Tareas" value={s.tasks} hint={`${s.open_tasks} abiertas · ${s.overdue_tasks} vencidas`} icon={<ListChecks className="h-4 w-4" />} tone="slate" />
        <Kpi label="Miembros" value={s.members} hint="en tus áreas" icon={<Users className="h-4 w-4" />} tone="brand" />
      </div>
      <Panel title="Áreas que administras">
        <div className="flex flex-wrap gap-2">
          {(scope.data?.areas ?? []).map((a) => (
            <span key={a.id} className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">
              {a.name}
            </span>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function ActividadTab() {
  const q = useQuery({ queryKey: ["area-admin", "activity"], queryFn: () => getAreaAdminActivity(12) });
  if (q.isLoading) return <Spinner label="Cargando actividad…" />;
  const a = q.data;
  if (!a) return null;
  const empty = (t: string) => <li className="px-2 py-3 text-sm text-slate-400">{t}</li>;
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Panel title="Proyectos creados recientemente" bodyClassName="px-3 py-1.5">
        <ul className="divide-y divide-slate-100">
          {a.recent_projects.length === 0
            ? empty("Sin proyectos recientes.")
            : a.recent_projects.map((p) => {
                const st = PROJECT_STATUS[p.status as ProjectStatus] ?? { label: p.status, tone: "neutral" as const };
                return (
                  <li key={p.id} className="flex items-start justify-between gap-3 px-2 py-2.5">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-800" title={p.name}>{p.name}</div>
                      <div className="truncate text-xs text-slate-400">
                        {p.area_name ?? "—"}{p.owner_name ? ` · ${p.owner_name}` : ""}
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <Badge tone={st.tone}>{st.label}</Badge>
                      <span className="text-[11px] text-slate-400">{timeAgo(p.created_at)}</span>
                    </div>
                  </li>
                );
              })}
        </ul>
      </Panel>
      <Panel title="Tareas creadas recientemente" bodyClassName="px-3 py-1.5">
        <ul className="divide-y divide-slate-100">
          {a.recent_tasks.length === 0
            ? empty("Sin tareas recientes.")
            : a.recent_tasks.map((t) => {
                const st = TASK_STATUS[t.status] ?? { label: t.status, tone: "neutral" as const };
                return (
                  <li key={t.id} className="flex items-start justify-between gap-3 px-2 py-2.5">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-800" title={t.title}>{t.title}</div>
                      <div className="truncate text-xs text-slate-400">
                        {t.project_name ?? "—"}{t.assignee_name ? ` · ${t.assignee_name}` : " · sin asignar"}
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <Badge tone={st.tone}>{st.label}</Badge>
                      <span className="text-[11px] text-slate-400">{timeAgo(t.created_at)}</span>
                    </div>
                  </li>
                );
              })}
        </ul>
      </Panel>
    </div>
  );
}

function TareasTab() {
  const q = useQuery({ queryKey: ["area-admin", "tasks"], queryFn: getAreaAdminTasks });
  if (q.isLoading) return <Spinner label="Cargando tareas…" />;
  if (!q.data) return null;
  return <TaskSummaryView data={q.data} />;
}

function MiembrosTab() {
  const qc = useQueryClient();
  const members = useQuery({ queryKey: ["area-admin", "members"], queryFn: getAreaAdminMembers });
  const scope = useQuery({ queryKey: ["area-admin", "scope"], queryFn: getAreaAdminScope });
  const users = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["area-admin", "members"] });

  const [areaId, setAreaId] = useState<number | "">("");
  const [userId, setUserId] = useState<number | "">("");
  const [role, setRole] = useState("member");

  const add = useMutation({
    mutationFn: () => setAreaMember(Number(areaId), Number(userId), role),
    onSuccess: () => {
      invalidate();
      setUserId("");
    },
  });
  const changeRole = useMutation({
    mutationFn: ({ aId, uId, r }: { aId: number; uId: number; r: string }) => setAreaMember(aId, uId, r),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: ({ aId, uId }: { aId: number; uId: number }) => removeAreaMember(aId, uId),
    onSuccess: invalidate,
  });

  if (members.isLoading) return <Spinner label="Cargando miembros…" />;
  const rows = members.data?.members ?? [];
  const areas = scope.data?.areas ?? [];
  const allUsers = users.data ?? [];

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (areaId !== "" && userId !== "") add.mutate();
          }}
          className="flex flex-wrap items-end gap-3"
        >
          <div className="w-44">
            <Select label="Área" value={areaId} onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Selecciona…</option>
              {areas.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
            </Select>
          </div>
          <div className="w-56">
            <Select label="Persona" value={userId} onChange={(e) => setUserId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Selecciona…</option>
              {allUsers.map((u) => (<option key={u.id} value={u.id}>{u.name}</option>))}
            </Select>
          </div>
          <div className="w-56">
            <Select label="Rol" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="member">Miembro</option>
              <option value="lead">Administrador de área</option>
            </Select>
          </div>
          <Button type="submit" disabled={areaId === "" || userId === "" || add.isPending}>
            {add.isPending ? "Agregando…" : "Agregar / actualizar"}
          </Button>
        </form>
      </Card>

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2.5">Persona</th>
                <th className="px-4 py-2.5">Área</th>
                <th className="px-4 py-2.5">Rol</th>
                <th className="px-4 py-2.5 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-6 text-center text-sm text-slate-400">Sin miembros.</td></tr>
              ) : (
                rows.map((m) => (
                  <tr key={`${m.area_id}-${m.user_id}`} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-slate-900">{m.name}</div>
                      <div className="text-xs text-slate-400">{m.email}</div>
                    </td>
                    <td className="px-4 py-2.5 text-slate-600">{m.area_name}</td>
                    <td className="px-4 py-2.5">
                      <Select
                        className="h-8 w-52 text-xs"
                        value={m.area_role === "lead" || m.area_role === "admin" ? "lead" : "member"}
                        onChange={(e) => changeRole.mutate({ aId: m.area_id, uId: m.user_id, r: e.target.value })}
                      >
                        <option value="member">Miembro</option>
                        <option value="lead">Administrador de área</option>
                      </Select>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(`¿Quitar a ${m.name} de ${m.area_name}?`))
                            remove.mutate({ aId: m.area_id, uId: m.user_id });
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Quitar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
      <p className="text-xs text-slate-400">
        "Administrador de área" puede administrar los proyectos, tareas y miembros de esa área.
        Solo puedes gestionar las áreas que tú administras.
      </p>
    </div>
  );
}

const TABS = [
  { key: "resumen", label: "Resumen", icon: LayoutDashboard },
  { key: "actividad", label: "Actividad", icon: Activity },
  { key: "tareas", label: "Tareas", icon: ListChecks },
  { key: "miembros", label: "Miembros", icon: Users },
] as const;

type AreaAdminTab = (typeof TABS)[number]["key"];

export default function AreaAdminPage() {
  const me = useMe();
  const [tab, setTab] = useState<AreaAdminTab>("resumen");

  const administers =
    me.data?.is_superadmin ||
    me.data?.areas?.some((a) => a.area_role === "lead" || a.area_role === "admin");

  if (me.data && !administers) {
    return (
      <Panel>
        <p className="text-sm text-slate-500">
          No administras ningún área. Pídele a un administrador que te asigne como administrador de
          un área.
        </p>
      </Panel>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Administración de área"
        title="Mi área"
        description="Gestiona los proyectos, tareas y miembros de las áreas que administras."
      />
      <div className="inline-flex flex-wrap gap-0.5 rounded-xl border border-slate-200 bg-white p-0.5 text-sm font-medium shadow-card">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${
              tab === key ? "bg-brand-600 text-white" : "text-slate-500 hover:bg-slate-100"
            }`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>

      {tab === "resumen" ? (
        <ResumenTab />
      ) : tab === "actividad" ? (
        <ActividadTab />
      ) : tab === "tareas" ? (
        <TareasTab />
      ) : (
        <MiembrosTab />
      )}

      <p className="text-xs text-slate-400">
        <Link to="/proyectos" className="text-brand-600 hover:underline">Ir a proyectos</Link> para
        crear o editar los de tu área.
      </p>
    </div>
  );
}
