import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  PROJECT_STATUS,
  type ProjectStatus,
  addMember,
  deleteProject,
  getProject,
  listMembers,
  removeMember,
  updateProject,
} from "../api/projects";
import { listUsers } from "../api/users";
import { useMe } from "../auth/useAuth";
import AnalyticsPanel from "../components/AnalyticsPanel";
import AuditPanel from "../components/AuditPanel";
import EconomicsPanel from "../components/EconomicsPanel";
import GooglePanel from "../components/GooglePanel";
import KnowledgePanel from "../components/KnowledgePanel";
import SprintsPanel from "../components/SprintsPanel";
import TasksBoard from "../components/TasksBoard";
import { Badge, Button, Card, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";

export default function ProjectDetailPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const me = useMe();

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const membersQuery = useQuery({
    queryKey: ["project", projectId, "members"],
    queryFn: () => listMembers(projectId),
  });
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: listUsers });

  const updateStatus = useMutation({
    mutationFn: (status: ProjectStatus) => updateProject(projectId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
  });
  const assignOwner = useMutation({
    mutationFn: (ownerId: number | null) => updateProject(projectId, { owner_id: ownerId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
  });
  const addMemberMut = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: string }) =>
      addMember(projectId, userId, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId, "members"] }),
  });
  const removeMemberMut = useMutation({
    mutationFn: (userId: number) => removeMember(projectId, userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId, "members"] }),
  });
  const deleteMut = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => navigate("/proyectos", { replace: true }),
  });

  const [newMemberId, setNewMemberId] = useState<number | "">("");
  const [newMemberRole, setNewMemberRole] = useState("editor");

  const [plan, setPlan] = useState({ progress: "", start: "", due: "" });
  const [desc, setDesc] = useState("");
  useEffect(() => {
    const p = projectQuery.data;
    if (p) {
      setPlan({ progress: String(p.progress ?? 0), start: p.start_date ?? "", due: p.due_date ?? "" });
      setDesc(p.description ?? "");
    }
  }, [projectQuery.data]);
  const savePlan = useMutation({
    mutationFn: () =>
      updateProject(projectId, {
        progress: plan.progress === "" ? 0 : Number(plan.progress),
        start_date: plan.start || null,
        due_date: plan.due || null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
  });
  const saveDesc = useMutation({
    mutationFn: () => updateProject(projectId, { description: desc.trim() || null }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
  });

  if (projectQuery.isLoading) return <Spinner label="Cargando proyecto…" />;
  if (projectQuery.isError || !projectQuery.data) {
    return (
      <div className="space-y-4">
        <Link
          to="/proyectos"
          className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Proyectos
        </Link>
        <p className="text-sm text-red-600">No se encontró el proyecto.</p>
      </div>
    );
  }

  const project = projectQuery.data;
  const st = PROJECT_STATUS[project.status] ?? { label: project.status, tone: "neutral" as const };
  const isOwnerOrAdmin = me.data?.role === "admin" || me.data?.id === project.owner_id;
  const members = membersQuery.data ?? [];
  const canEdit =
    isOwnerOrAdmin ||
    members.some(
      (m) => m.user_id === me.data?.id && (m.role === "owner" || m.role === "editor"),
    );
  const memberIds = new Set(members.map((m) => m.user_id));
  const candidateUsers = (usersQuery.data ?? []).filter((u) => !memberIds.has(u.id));

  return (
    <div className="space-y-6">
      <Link
        to="/proyectos"
        className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Proyectos
      </Link>

      <PageHeader
        title={project.name}
        description={project.description ?? undefined}
        actions={
          isOwnerOrAdmin ? (
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                if (window.confirm("¿Eliminar el proyecto?")) deleteMut.mutate();
              }}
            >
              <Trash2 className="h-4 w-4" /> Eliminar
            </Button>
          ) : null
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={st.tone}>{st.label}</Badge>
        <Badge tone="neutral">{project.area_name}</Badge>
        {project.owner_name && (
          <span className="text-sm text-slate-500">Responsable: {project.owner_name}</span>
        )}
        {project.due_date && (
          <span className="text-sm text-slate-500">
            · Entrega: {new Date(project.due_date).toLocaleDateString("es-CO")}
          </span>
        )}
      </div>

      {canEdit && (
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Descripción</h2>
          <Textarea
            rows={3}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Describe el objetivo, alcance o contexto del proyecto…"
          />
          <div className="mt-3 flex justify-end">
            <Button size="sm" onClick={() => saveDesc.mutate()} disabled={saveDesc.isPending}>
              {saveDesc.isPending ? "Guardando…" : "Guardar descripción"}
            </Button>
          </div>
        </Card>
      )}

      {canEdit && (
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Estado y responsable</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Estado"
              value={project.status}
              onChange={(e) => updateStatus.mutate(e.target.value as ProjectStatus)}
            >
              {Object.entries(PROJECT_STATUS).map(([key, value]) => (
                <option key={key} value={key}>
                  {value.label}
                </option>
              ))}
            </Select>
            <Select
              label="Responsable"
              value={project.owner_id ?? ""}
              onChange={(e) => assignOwner.mutate(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Sin responsable</option>
              {(usersQuery.data ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </Select>
          </div>
        </Card>
      )}

      {canEdit && (
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Planificación y avance</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <Input
              label="Avance (%)"
              type="number"
              min="0"
              max="100"
              value={plan.progress}
              onChange={(e) => setPlan({ ...plan, progress: e.target.value })}
            />
            <Input
              label="Inicio"
              type="date"
              value={plan.start}
              onChange={(e) => setPlan({ ...plan, start: e.target.value })}
            />
            <Input
              label="Entrega"
              type="date"
              value={plan.due}
              onChange={(e) => setPlan({ ...plan, due: e.target.value })}
            />
          </div>
          <div className="mt-3 flex items-center gap-3">
            <Button size="sm" onClick={() => savePlan.mutate()} disabled={savePlan.isPending}>
              {savePlan.isPending ? "Guardando…" : "Guardar"}
            </Button>
            <div className="h-1.5 flex-1 rounded-full bg-slate-100">
              <div
                className="h-1.5 rounded-full bg-brand-500"
                style={{ width: `${Math.min(100, Number(plan.progress) || 0)}%` }}
              />
            </div>
          </div>
        </Card>
      )}

      <AnalyticsPanel projectId={projectId} />

      <EconomicsPanel projectId={projectId} canEdit={canEdit} />

      <SprintsPanel projectId={projectId} canEdit={canEdit} />

      <TasksBoard projectId={projectId} canEdit={canEdit} users={usersQuery.data ?? []} />

      <GooglePanel projectId={projectId} canEdit={canEdit} />

      <KnowledgePanel projectId={projectId} canEdit={canEdit} />

      <AuditPanel projectId={projectId} />

      <Card className="p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-700">Miembros</h2>
        {membersQuery.isLoading ? (
          <Spinner label="Cargando…" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between py-2">
                <div>
                  <div className="text-sm font-medium text-slate-900">{m.name}</div>
                  <div className="text-xs text-slate-500">{m.email}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={m.role === "owner" ? "brand" : "neutral"}>{m.role}</Badge>
                  {isOwnerOrAdmin && m.role !== "owner" && (
                    <button
                      type="button"
                      onClick={() => removeMemberMut.mutate(m.user_id)}
                      title="Quitar"
                      className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {isOwnerOrAdmin && candidateUsers.length > 0 && (
          <div className="mt-4 flex items-end gap-2 border-t border-slate-100 pt-4">
            <Select
              label="Añadir miembro"
              value={newMemberId}
              onChange={(e) => setNewMemberId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Selecciona usuario</option>
              {candidateUsers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </Select>
            <Select label="Rol" value={newMemberRole} onChange={(e) => setNewMemberRole(e.target.value)}>
              <option value="editor">editor</option>
              <option value="viewer">viewer</option>
            </Select>
            <Button
              onClick={() => {
                if (newMemberId !== "") {
                  addMemberMut.mutate({ userId: Number(newMemberId), role: newMemberRole });
                  setNewMemberId("");
                }
              }}
              disabled={newMemberId === ""}
            >
              <UserPlus className="h-4 w-4" /> Añadir
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
