import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Pencil, Plus, ShieldCheck, Users } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  type AdminArea,
  type AdminUser,
  createAdminArea,
  createAdminUser,
  listAdminAreas,
  listAdminUsers,
  resetUser2fa,
  setUserAreas,
  updateAdminArea,
  updateAdminUser,
} from "../api/admin";
import { useMe } from "../auth/useAuth";
import {
  Badge,
  Button,
  Card,
  Input,
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
  const [eRole, setERole] = useState("member");
  const [eActive, setEActive] = useState(true);
  const [eAreas, setEAreas] = useState<number[]>([]);

  const openEdit = (u: AdminUser) => {
    setEditUser(u);
    setEName(u.name);
    setERole(u.role);
    setEActive(u.is_active);
    setEAreas(u.areas.map((a) => a.area_id));
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
      await updateAdminUser(editUser!.id, { name: eName.trim(), role: eRole, is_active: eActive });
      return setUserAreas(editUser!.id, eAreas.map((area_id) => ({ area_id, area_role: "member" })));
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

      <Modal open={editUser !== null} onClose={() => setEditUser(null)} title={`Editar ${editUser?.email ?? ""}`}>
        <div className="space-y-4">
          <Input label="Nombre" value={eName} onChange={(e) => setEName(e.target.value)} />
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
            <div className="mb-1.5 text-sm font-medium text-slate-700">Áreas</div>
            <div className="flex flex-wrap gap-2">
              {allAreas.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setEAreas((l) => toggle(l, a.id))}
                  className={`rounded-full px-3 py-1 text-sm font-medium transition ${eAreas.includes(a.id) ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                >
                  {a.name}
                </button>
              ))}
            </div>
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
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <Button variant="secondary" onClick={() => setEditUser(null)}>Cancelar</Button>
            <Button onClick={() => saveUser.mutate()} disabled={!eName.trim() || saveUser.isPending}>
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

export default function AdminPage() {
  const me = useMe();
  const [tab, setTab] = useState<"users" | "areas">("users");

  if (me.data && me.data.role !== "admin") {
    return (
      <Panel>
        <p className="text-sm text-slate-500">Esta sección es solo para administradores.</p>
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
      <div className="inline-flex rounded-xl border border-slate-200 bg-white p-0.5 text-sm font-medium shadow-card">
        <button
          type="button"
          onClick={() => setTab("users")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${tab === "users" ? "bg-brand-600 text-white" : "text-slate-500 hover:bg-slate-100"}`}
        >
          <Users className="h-4 w-4" /> Usuarios
        </button>
        <button
          type="button"
          onClick={() => setTab("areas")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${tab === "areas" ? "bg-brand-600 text-white" : "text-slate-500 hover:bg-slate-100"}`}
        >
          <Building2 className="h-4 w-4" /> Áreas
        </button>
      </div>

      {tab === "users" ? <UsersTab /> : <AreasTab />}

      <p className="flex items-center gap-1.5 text-xs text-slate-400">
        <ShieldCheck className="h-3.5 w-3.5" /> Alcance total: solo administradores ven esta sección.
      </p>
    </div>
  );
}
