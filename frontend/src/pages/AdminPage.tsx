import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  Cloud,
  FolderKanban,
  LayoutDashboard,
  ListChecks,
  LogIn,
  Pencil,
  Plus,
  ShieldCheck,
  Sparkles,
  Tags,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  type AdminArea,
  type AdminUser,
  createAdminArea,
  createAdminUser,
  getAdminActivity,
  getAdminStats,
  listAdminAreas,
  listAdminUsers,
  resetUser2fa,
  setUserAreas,
  updateAdminArea,
  updateAdminUser,
} from "../api/admin";
import {
  PROJECT_STATUS,
  type Project,
  type ProjectStatus,
  deleteProject,
  listProjects,
  updateProject,
} from "../api/projects";
import { getAdminTaskSummary } from "../api/tasks";
import { listUsers } from "../api/users";
import { useMe } from "../auth/useAuth";
import { CatalogManager } from "../components/CatalogManager";
import { TaskSummaryView } from "../components/TaskSummaryView";
import {
  Badge,
  Button,
  Card,
  Input,
  Kpi,
  Modal,
  PageHeader,
  Panel,
  Select,
  Spinner,
  Textarea,
} from "../components/ui";

const toggle = (list: number[], id: number) =>
  list.includes(id) ? list.filter((x) => x !== id) : [...list, id];

function UsersTab() {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["admin-users"], queryFn: listAdminUsers });
  const areas = useQuery({ queryKey: ["admin-areas"], queryFn: listAdminAreas });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-users"] });
  const allAreas = areas.data ?? [];

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("member");
  const [newAreas, setNewAreas] = useState<number[]>([]);

  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [eName, setEName] = useState("");
  const [eEmail, setEEmail] = useState("");
  const [eRole, setERole] = useState("member");
  const [eActive, setEActive] = useState(true);
  const [eCanViewCosts, setECanViewCosts] = useState(false);
  const [eAreaRoles, setEAreaRoles] = useState<Record<number, string>>({});

  const openEdit = (u: AdminUser) => {
    setEditUser(u);
    setEName(u.name);
    setEEmail(u.email);
    setERole(u.role);
    setEActive(u.is_active);
    setECanViewCosts(u.can_view_costs);
    setEAreaRoles(Object.fromEntries(u.areas.map((a) => [a.area_id, a.area_role])));
  };

  const create = useMutation({
    mutationFn: () => createAdminUser({ email: email.trim(), name: name.trim(), role, area_ids: newAreas }),
    onSuccess: () => {
      invalidate();
      setShowForm(false);
      setEmail("");
      setName("");
      setRole("member");
      setNewAreas([]);
    },
  });
  const saveUser = useMutation({
    mutationFn: async () => {
      await updateAdminUser(editUser!.id, {
        name: eName.trim(),
        email: eEmail.trim(),
        role: eRole,
        is_active: eActive,
        can_view_costs: eCanViewCosts,
      });
      return setUserAreas(
        editUser!.id,
        Object.entries(eAreaRoles).map(([area_id, area_role]) => ({
          area_id: Number(area_id),
          area_role,
        })),
      );
    },
    onSuccess: () => {
      invalidate();
      setEditUser(null);
    },
  });
  const reset2fa = useMutation({
    mutationFn: () => resetUser2fa(editUser!.id),
    onSuccess: () => {
      invalidate();
      setEditUser((p) => (p ? { ...p, twofa_enabled: false } : p));
    },
  });

  if (users.isLoading) return <Spinner label="Cargando usuarios…" />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowForm((v) => !v)} variant={showForm ? "secondary" : "primary"}>
          <Plus className="h-4 w-4" /> Nuevo usuario
        </Button>
      </div>

      {showForm && (
        <Card className="p-5">
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (email.trim() && name.trim()) create.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 sm:grid-cols-3">
              <Input label="Correo" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="persona@invesa.com" />
              <Input label="Nombre" value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre y apellido" />
              <Select label="Rol" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="member">Miembro</option>
                <option value="admin">Administrador</option>
              </Select>
            </div>
            <div>
              <div className="mb-1.5 text-sm font-medium text-slate-700">Áreas</div>
              <div className="flex flex-wrap gap-2">
                {allAreas.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => setNewAreas((l) => toggle(l, a.id))}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${newAreas.includes(a.id) ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                  >
                    {a.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancelar</Button>
              <Button type="submit" disabled={!email.trim() || !name.trim() || create.isPending}>
                {create.isPending ? "Creando…" : "Crear usuario"}
              </Button>
            </div>
            {create.isError && <p className="text-sm text-red-600">{(create.error as Error).message}</p>}
          </form>
        </Card>
      )}

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2.5">Usuario</th>
                <th className="px-4 py-2.5">Rol</th>
                <th className="px-4 py-2.5">Áreas</th>
                <th className="px-4 py-2.5">2FA</th>
                <th className="px-4 py-2.5">Costos</th>
                <th className="px-4 py-2.5">Estado</th>
                <th className="px-4 py-2.5 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(users.data ?? []).map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-slate-900">{u.name}</div>
                    <div className="text-xs text-slate-400">{u.email}</div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={u.role === "admin" ? "brand" : "neutral"}>
                      {u.role === "admin" ? "Administrador" : "Miembro"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {u.areas.length === 0 ? (
                        <span className="text-xs text-slate-400">—</span>
                      ) : (
                        u.areas.map((a) => (
                          <span key={a.area_id} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                            {a.name}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={u.twofa_enabled ? "success" : "neutral"} dot>
                      {u.twofa_enabled ? "Activo" : "—"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={u.can_view_costs ? "brand" : "neutral"}>
                      {u.can_view_costs ? "Solo vista" : "—"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={u.is_active ? "success" : "neutral"}>{u.is_active ? "Activo" : "Inactivo"}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      type="button"
                      onClick={() => openEdit(u)}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                    >
                      <Pencil className="h-3.5 w-3.5" /> Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={editUser !== null} onClose={() => setEditUser(null)} title={`Editar ${editUser?.email ?? ""}`} size="xl">
        <div className="space-y-4">
          <Input label="Nombre" value={eName} onChange={(e) => setEName(e.target.value)} />
          <Input
            label="Correo"
            type="email"
            value={eEmail}
            onChange={(e) => setEEmail(e.target.value)}
            placeholder="persona@invesa.com"
          />
          <div className="grid grid-cols-2 gap-3">
            <Select label="Rol" value={eRole} onChange={(e) => setERole(e.target.value)}>
              <option value="member">Miembro</option>
              <option value="admin">Administrador</option>
            </Select>
            <div>
              <div className="mb-1.5 text-sm font-medium text-slate-700">Estado</div>
              <button
                type="button"
                onClick={() => setEActive((v) => !v)}
                className={`h-10 w-full rounded-xl border text-sm font-medium transition ${eActive ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-500"}`}
              >
                {eActive ? "Activo" : "Inactivo"}
              </button>
            </div>
          </div>
          <div>
            <div className="mb-1.5 text-sm font-medium text-slate-700">Módulo de Costos</div>
            <button
              type="button"
              onClick={() => setECanViewCosts((v) => !v)}
              className={`h-10 rounded-xl border px-4 text-sm font-medium transition ${eCanViewCosts ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-500"}`}
            >
              {eCanViewCosts ? "Con acceso" : "Sin acceso"}
            </button>
          </div>
          <div>
            <div className="mb-1.5 text-sm font-medium text-slate-700">Áreas y rol</div>
            <div className="space-y-1.5">
              {allAreas.map((a) => (
                <div key={a.id} className="grid grid-cols-[1fr_15rem] items-center gap-3">
                  <span className="truncate text-sm text-slate-700">{a.name}</span>
                  <Select
                    className="h-9 text-sm"
                    value={eAreaRoles[a.id] ?? ""}
                    onChange={(e) =>
                      setEAreaRoles((prev) => {
                        const next = { ...prev };
                        if (e.target.value === "") delete next[a.id];
                        else next[a.id] = e.target.value;
                        return next;
                      })
                    }
                  >
                    <option value="">Sin acceso</option>
                    <option value="member">Miembro</option>
                    <option value="lead">Administrador de área</option>
                  </Select>
                </div>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-400">
              "Administrador de área" puede gestionar los proyectos, tareas y miembros de esa área.
            </p>
          </div>
          {editUser?.twofa_enabled && (
            <div className="flex items-center justify-between rounded-xl border border-amber-100 bg-amber-50 px-3 py-2.5 text-sm">
              <span className="text-amber-700">2FA activo en esta cuenta.</span>
              <button
                type="button"
                onClick={() => reset2fa.mutate()}
                disabled={reset2fa.isPending}
                className="rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-amber-200 transition hover:bg-amber-100"
              >
                {reset2fa.isPending ? "Restableciendo…" : "Restablecer 2FA"}
              </button>
            </div>
          )}
          {saveUser.isError && (
            <p className="text-sm text-rose-600">
              {(saveUser.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                "No se pudieron guardar los cambios."}
            </p>
          )}
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <Button variant="secondary" onClick={() => setEditUser(null)}>Cancelar</Button>
            <Button
              onClick={() => saveUser.mutate()}
              disabled={!eName.trim() || !eEmail.trim() || saveUser.isPending}
            >
              {saveUser.isPending ? "Guardando…" : "Guardar cambios"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function AreasTab() {
  const qc = useQueryClient();
  const areas = useQuery({ queryKey: ["admin-areas"], queryFn: listAdminAreas });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-areas"] });
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [edit, setEdit] = useState<AdminArea | null>(null);
  const [eName, setEName] = useState("");
  const [eDesc, setEDesc] = useState("");
  const [eActive, setEActive] = useState(true);

  const openEdit = (a: AdminArea) => {
    setEdit(a);
    setEName(a.name);
    setEDesc(a.description ?? "");
    setEActive(a.is_active);
  };

  const create = useMutation({
    mutationFn: () => createAdminArea({ name: name.trim(), description: description.trim() || null }),
    onSuccess: () => {
      invalidate();
      setShowForm(false);
      setName("");
      setDescription("");
    },
  });
  const save = useMutation({
    mutationFn: () =>
      updateAdminArea(edit!.id, { name: eName.trim(), description: eDesc.trim() || null, is_active: eActive }),
    onSuccess: () => {
      invalidate();
      setEdit(null);
    },
  });

  if (areas.isLoading) return <Spinner label="Cargando áreas…" />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowForm((v) => !v)} variant={showForm ? "secondary" : "primary"}>
          <Plus className="h-4 w-4" /> Nueva área
        </Button>
      </div>
      {showForm && (
        <Card className="p-5">
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (name.trim()) create.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Nombre" value={name} onChange={(e) => setName(e.target.value)} placeholder="p. ej. Producción" />
              <Input label="Descripción (opcional)" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancelar</Button>
              <Button type="submit" disabled={!name.trim() || create.isPending}>
                {create.isPending ? "Creando…" : "Crear área"}
              </Button>
            </div>
            {create.isError && <p className="text-sm text-red-600">{(create.error as Error).message}</p>}
          </form>
        </Card>
      )}
      <Card className="divide-y divide-slate-100 overflow-hidden">
        {(areas.data ?? []).map((a) => (
          <div key={a.id} className="flex items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              <div className="font-medium text-slate-900">{a.name}</div>
              <div className="truncate text-xs text-slate-400">/{a.slug}{a.description ? ` · ${a.description}` : ""}</div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge tone={a.is_active ? "success" : "neutral"}>{a.is_active ? "Activa" : "Inactiva"}</Badge>
              <button
                type="button"
                onClick={() => openEdit(a)}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
              >
                <Pencil className="h-3.5 w-3.5" /> Editar
              </button>
            </div>
          </div>
        ))}
      </Card>

      <Modal open={edit !== null} onClose={() => setEdit(null)} title={`Editar área`}>
        <div className="space-y-4">
          <Input label="Nombre" value={eName} onChange={(e) => setEName(e.target.value)} />
          <Textarea label="Descripción" rows={2} value={eDesc} onChange={(e) => setEDesc(e.target.value)} />
          <div>
            <div className="mb-1.5 text-sm font-medium text-slate-700">Estado</div>
            <button
              type="button"
              onClick={() => setEActive((v) => !v)}
              className={`h-10 rounded-xl border px-4 text-sm font-medium transition ${eActive ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-500"}`}
            >
              {eActive ? "Activa" : "Inactiva"}
            </button>
          </div>
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <Button variant="secondary" onClick={() => setEdit(null)}>Cancelar</Button>
            <Button onClick={() => save.mutate()} disabled={!eName.trim() || save.isPending}>
              {save.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function ResumenTab() {
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: getAdminStats });
  if (stats.isLoading) return <Spinner label="Cargando…" />;
  const s = stats.data;
  if (!s) return null;
  const label = (v: string) => (v === "real" ? "Real" : "Simulado");
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Usuarios" value={s.users} hint={`${s.active_users} activos · ${s.admins} admin`} icon={<Users className="h-4 w-4" />} tone="brand" />
        <Kpi label="Áreas" value={s.areas} hint="organizativas" icon={<Building2 className="h-4 w-4" />} tone="brand" />
        <Kpi label="Proyectos" value={s.projects} hint={`${s.active_projects} activos`} icon={<FolderKanban className="h-4 w-4" />} tone="emerald" />
        <Kpi label="Tareas" value={s.tasks} hint={`${s.open_tasks} abiertas · ${s.overdue_tasks} vencidas`} icon={<LayoutDashboard className="h-4 w-4" />} tone="slate" />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Integraciones">
          <ul className="space-y-3 text-sm">
            <li className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-slate-700"><Cloud className="h-4 w-4 text-slate-400" /> Google Workspace</span>
              <Badge tone={s.google_provider === "real" ? "success" : "neutral"} dot>{label(s.google_provider)}</Badge>
            </li>
            <li className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-slate-700"><Sparkles className="h-4 w-4 text-slate-400" /> Asistente IA (Gemini)</span>
              <Badge tone={s.gemini_provider === "real" ? "success" : "neutral"} dot>{label(s.gemini_provider)}</Badge>
            </li>
          </ul>
        </Panel>
        <Panel title="Seguridad">
          <ul className="space-y-3 text-sm">
            <li className="flex items-center justify-between">
              <span className="text-slate-700">Administradores</span>
              <span className="font-semibold text-slate-900">{s.admins}</span>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-slate-700">Usuarios con 2FA activo</span>
              <span className="font-semibold text-slate-900">{s.two_fa} / {s.users}</span>
            </li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}

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
  if (mo < 12) return `hace ${mo} ${mo === 1 ? "mes" : "meses"}`;
  const y = Math.floor(mo / 12);
  return `hace ${y} ${y === 1 ? "año" : "años"}`;
}

const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });

const TASK_STATUS = {
  todo: { label: "Por hacer", tone: "neutral" },
  in_progress: { label: "En curso", tone: "brand" },
  blocked: { label: "Bloqueada", tone: "danger" },
  done: { label: "Hecha", tone: "success" },
} as const;

const panelTitle = (icon: JSX.Element, text: string) => (
  <span className="flex items-center gap-2">
    {icon}
    {text}
  </span>
);

function RoleBadge({ role }: { role: string }) {
  return <Badge tone={role === "admin" ? "brand" : "neutral"}>{role === "admin" ? "Admin" : "Miembro"}</Badge>;
}

function UserRow({ name, email, role, at }: { name: string; email: string; role: string; at: string }) {
  return (
    <li className="flex items-center justify-between gap-3 px-2 py-2.5">
      <div className="min-w-0">
        <div className="truncate font-medium text-slate-800">{name}</div>
        <div className="truncate text-xs text-slate-400">{email}</div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <RoleBadge role={role} />
        <span className="text-[11px] text-slate-400" title={fmtDateTime(at)}>{timeAgo(at)}</span>
      </div>
    </li>
  );
}

function ActividadTab() {
  const activity = useQuery({ queryKey: ["admin-activity"], queryFn: () => getAdminActivity(12) });
  if (activity.isLoading) return <Spinner label="Cargando actividad…" />;
  const a = activity.data;
  if (!a) return null;
  const empty = (t: string) => <li className="px-2 py-3 text-sm text-slate-400">{t}</li>;
  const listBody = "px-3 py-1.5";

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Panel title={panelTitle(<FolderKanban className="h-4 w-4 text-slate-400" />, "Proyectos creados recientemente")} bodyClassName={listBody}>
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
                      <span className="text-[11px] text-slate-400" title={fmtDateTime(p.created_at)}>{timeAgo(p.created_at)}</span>
                    </div>
                  </li>
                );
              })}
        </ul>
      </Panel>

      <Panel title={panelTitle(<ListChecks className="h-4 w-4 text-slate-400" />, "Tareas creadas recientemente")} bodyClassName={listBody}>
        <ul className="divide-y divide-slate-100">
          {a.recent_tasks.length === 0
            ? empty("Sin tareas recientes.")
            : a.recent_tasks.map((t) => {
                const st = TASK_STATUS[t.status as keyof typeof TASK_STATUS] ?? { label: t.status, tone: "neutral" as const };
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
                      <span className="text-[11px] text-slate-400" title={fmtDateTime(t.created_at)}>{timeAgo(t.created_at)}</span>
                    </div>
                  </li>
                );
              })}
        </ul>
      </Panel>

      <Panel title={panelTitle(<LogIn className="h-4 w-4 text-slate-400" />, "Últimos ingresos")} bodyClassName={listBody}>
        <ul className="divide-y divide-slate-100">
          {a.recent_logins.length === 0
            ? empty("Aún no hay ingresos registrados.")
            : a.recent_logins.map((u) => (
                <UserRow key={u.id} name={u.name} email={u.email} role={u.role} at={u.at} />
              ))}
        </ul>
      </Panel>

      <Panel title={panelTitle(<UserPlus className="h-4 w-4 text-slate-400" />, "Usuarios registrados recientemente")} bodyClassName={listBody}>
        <ul className="divide-y divide-slate-100">
          {a.recent_users.length === 0
            ? empty("Sin usuarios.")
            : a.recent_users.map((u) => (
                <UserRow key={u.id} name={u.name} email={u.email} role={u.role} at={u.at} />
              ))}
        </ul>
      </Panel>
    </div>
  );
}

function ProjectsTab() {
  const qc = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const users = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["admin-stats"] });
  };
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { owner_id?: number | null; status?: ProjectStatus } }) =>
      updateProject(id, body),
    onSuccess: invalidate,
  });
  const del = useMutation({ mutationFn: (id: number) => deleteProject(id), onSuccess: invalidate });

  if (projects.isLoading) return <Spinner label="Cargando proyectos…" />;
  const list = projects.data ?? [];
  const allUsers = users.data ?? [];

  return (
    <Card className="overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <th className="px-4 py-2.5">Proyecto</th>
              <th className="px-4 py-2.5">Responsable</th>
              <th className="px-4 py-2.5">Estado</th>
              <th className="px-4 py-2.5">Avance</th>
              <th className="px-4 py-2.5 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {list.map((p: Project) => (
              <tr key={p.id} className="hover:bg-slate-50">
                <td className="px-4 py-2.5">
                  <div className="max-w-[280px] truncate font-medium text-slate-900" title={p.name}>{p.name}</div>
                  <div className="text-xs text-slate-400">{p.area_name}</div>
                </td>
                <td className="px-4 py-2.5">
                  <Select
                    className="h-8 w-44 text-xs"
                    value={p.owner_id ?? ""}
                    onChange={(e) => patch.mutate({ id: p.id, body: { owner_id: e.target.value ? Number(e.target.value) : null } })}
                  >
                    <option value="">Sin responsable</option>
                    {allUsers.map((u) => (<option key={u.id} value={u.id}>{u.name}</option>))}
                  </Select>
                </td>
                <td className="px-4 py-2.5">
                  <Select
                    className="h-8 w-36 text-xs"
                    value={p.status}
                    onChange={(e) => patch.mutate({ id: p.id, body: { status: e.target.value as ProjectStatus } })}
                  >
                    {Object.entries(PROJECT_STATUS).map(([k, v]) => (<option key={k} value={k}>{v.label}</option>))}
                  </Select>
                </td>
                <td className="px-4 py-2.5 tabular-nums text-slate-600">{p.progress}%</td>
                <td className="px-4 py-2.5 text-right">
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm(`¿Eliminar «${p.name}»?`)) del.mutate(p.id);
                    }}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function TareasTab() {
  const q = useQuery({ queryKey: ["admin-tasks"], queryFn: getAdminTaskSummary });
  if (q.isLoading) return <Spinner label="Cargando tareas…" />;
  if (!q.data) return null;
  return <TaskSummaryView data={q.data} />;
}

const TABS = [
  { key: "resumen", label: "Resumen", icon: LayoutDashboard },
  { key: "actividad", label: "Actividad", icon: Activity },
  { key: "projects", label: "Proyectos", icon: FolderKanban },
  { key: "tareas", label: "Tareas", icon: ListChecks },
  { key: "users", label: "Usuarios", icon: Users },
  { key: "areas", label: "Áreas", icon: Building2 },
  { key: "maestras", label: "Maestras", icon: Tags },
] as const;

type AdminTab = (typeof TABS)[number]["key"];

export default function AdminPage() {
  const me = useMe();
  const [tab, setTab] = useState<AdminTab>("resumen");

  if (me.data && !me.data.is_superadmin) {
    return (
      <Panel>
        <p className="text-sm text-slate-500">Esta sección es solo para el super administrador.</p>
      </Panel>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Administración"
        title="Configuración del sistema"
        description="Gestiona usuarios, roles, accesos por área, 2FA y la estructura de áreas."
      />
      <div className="inline-flex flex-wrap gap-0.5 rounded-xl border border-slate-200 bg-white p-0.5 text-sm font-medium shadow-card">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${tab === key ? "bg-brand-600 text-white" : "text-slate-500 hover:bg-slate-100"}`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>

      {tab === "resumen" ? (
        <ResumenTab />
      ) : tab === "actividad" ? (
        <ActividadTab />
      ) : tab === "projects" ? (
        <ProjectsTab />
      ) : tab === "tareas" ? (
        <TareasTab />
      ) : tab === "users" ? (
        <UsersTab />
      ) : tab === "areas" ? (
        <AreasTab />
      ) : (
        <CatalogManager />
      )}

      <p className="flex items-center gap-1.5 text-xs text-slate-400">
        <ShieldCheck className="h-3.5 w-3.5" /> Alcance total: solo administradores ven esta sección.
      </p>
    </div>
  );
}
