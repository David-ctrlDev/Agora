import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus, ShieldCheck, Users } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  type AdminUser,
  createAdminArea,
  createAdminUser,
  listAdminAreas,
  listAdminUsers,
  setUserAreas,
  updateAdminArea,
  updateAdminUser,
} from "../api/admin";
import { useMe } from "../auth/useAuth";
import { Badge, Button, Card, Input, Modal, PageHeader, Panel, Select, Spinner } from "../components/ui";

function UsersTab() {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["admin-users"], queryFn: listAdminUsers });
  const areas = useQuery({ queryKey: ["admin-areas"], queryFn: listAdminAreas });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin-users"] });

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("member");
  const [newAreas, setNewAreas] = useState<number[]>([]);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [editAreas, setEditAreas] = useState<number[]>([]);

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
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { role?: string; is_active?: boolean } }) =>
      updateAdminUser(id, body),
    onSuccess: invalidate,
  });
  const saveAreas = useMutation({
    mutationFn: () => setUserAreas(editing!.id, editAreas.map((area_id) => ({ area_id, area_role: "member" }))),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  const toggle = (list: number[], id: number) =>
    list.includes(id) ? list.filter((x) => x !== id) : [...list, id];

  const allAreas = areas.data ?? [];

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
                    <Select
                      className="h-8 w-36 text-xs"
                      value={u.role}
                      onChange={(e) => patch.mutate({ id: u.id, body: { role: e.target.value } })}
                    >
                      <option value="member">Miembro</option>
                      <option value="admin">Administrador</option>
                    </Select>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap items-center gap-1">
                      {u.areas.length === 0 ? (
                        <span className="text-xs text-slate-400">—</span>
                      ) : (
                        u.areas.map((a) => (
                          <span key={a.area_id} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                            {a.name}
                          </span>
                        ))
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          setEditing(u);
                          setEditAreas(u.areas.map((a) => a.area_id));
                        }}
                        className="rounded-full border border-dashed border-slate-300 px-2 py-0.5 text-xs text-slate-500 transition hover:border-brand-400 hover:text-brand-600"
                      >
                        editar
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={u.twofa_enabled ? "success" : "neutral"} dot>
                      {u.twofa_enabled ? "Activo" : "—"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5">
                    <button
                      type="button"
                      onClick={() => patch.mutate({ id: u.id, body: { is_active: !u.is_active } })}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition ${u.is_active ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}
                    >
                      {u.is_active ? "Activo" : "Inactivo"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={editing !== null} onClose={() => setEditing(null)} title={`Áreas de ${editing?.name ?? ""}`}>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {allAreas.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => setEditAreas((l) => toggle(l, a.id))}
                className={`rounded-full px-3 py-1 text-sm font-medium transition ${editAreas.includes(a.id) ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
              >
                {a.name}
              </button>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setEditing(null)}>Cancelar</Button>
            <Button onClick={() => saveAreas.mutate()} disabled={saveAreas.isPending}>
              {saveAreas.isPending ? "Guardando…" : "Guardar áreas"}
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

  const create = useMutation({
    mutationFn: () => createAdminArea({ name: name.trim(), description: description.trim() || null }),
    onSuccess: () => {
      invalidate();
      setShowForm(false);
      setName("");
      setDescription("");
    },
  });
  const patch = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => updateAdminArea(id, { is_active }),
    onSuccess: invalidate,
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
          <div key={a.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <div className="font-medium text-slate-900">{a.name}</div>
              <div className="text-xs text-slate-400">/{a.slug}{a.description ? ` · ${a.description}` : ""}</div>
            </div>
            <button
              type="button"
              onClick={() => patch.mutate({ id: a.id, is_active: !a.is_active })}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition ${a.is_active ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}
            >
              {a.is_active ? "Activa" : "Inactiva"}
            </button>
          </div>
        ))}
      </Card>
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
        description="Gestiona usuarios, roles, accesos por área y la estructura de áreas."
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
