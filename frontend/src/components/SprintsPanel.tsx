import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarRange, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import {
  SPRINT_STATUS,
  type SprintStatus,
  createSprint,
  deleteSprint,
  getBurndown,
  listSprints,
  updateSprint,
} from "../api/sprints";
import { TASK_STATUS, type Task, listProjectTasks, updateTask } from "../api/tasks";
import { BurndownChart } from "./charts";
import { Badge, Button, Card, Input, Select, Spinner } from "./ui";

function fmt(d: string) {
  return new Date(d).toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
}

const todayISO = () => new Date().toISOString().slice(0, 10);
const plusDaysISO = (days: number) =>
  new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);

function SprintDetail({
  sprintId,
  canEdit,
  status,
  tasks,
  onStatus,
  onDelete,
  onAssign,
}: {
  sprintId: number;
  canEdit: boolean;
  status: string;
  tasks: Task[];
  onStatus: (status: SprintStatus) => void;
  onDelete: () => void;
  onAssign: (taskId: number, sprintId: number | null) => void;
}) {
  const burndown = useQuery({ queryKey: ["burndown", sprintId], queryFn: () => getBurndown(sprintId) });
  const inSprint = tasks.filter((t) => t.sprint_id === sprintId);
  const unassigned = tasks.filter((t) => t.sprint_id == null);

  return (
    <div className="space-y-4 border-t border-slate-100 p-4">
      {canEdit && (
        <div className="flex items-center gap-2">
          <div className="w-44">
            <Select value={status} onChange={(e) => onStatus(e.target.value as SprintStatus)}>
              {Object.entries(SPRINT_STATUS).map(([key, value]) => (
                <option key={key} value={key}>
                  {value.label}
                </option>
              ))}
            </Select>
          </div>
          <Button size="sm" variant="danger" onClick={onDelete}>
            <Trash2 className="h-4 w-4" /> Eliminar
          </Button>
        </div>
      )}

      <div>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">Burndown</p>
        {!burndown.data ? (
          <Spinner label="Cargando…" />
        ) : burndown.data.total > 0 ? (
          <>
            <BurndownChart points={burndown.data.points} />
            <div className="flex gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-4 rounded" style={{ background: "#4f46e5" }} /> Real
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-0.5 w-4" style={{ background: "#cbd5e1" }} /> Ideal
              </span>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500">Asigna tareas al sprint para ver el burndown.</p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            Tareas del sprint ({inSprint.length})
          </p>
          <ul className="space-y-1.5">
            {inSprint.map((t) => {
              const meta = TASK_STATUS[t.status] ?? { label: t.status, tone: "neutral" as const };
              return (
                <li key={t.id} className="flex items-center gap-2 text-sm">
                  <Badge tone={meta.tone}>{meta.label}</Badge>
                  <span className="flex-1 truncate text-slate-700">{t.title}</span>
                  {canEdit && (
                    <button
                      type="button"
                      onClick={() => onAssign(t.id, null)}
                      title="Quitar del sprint"
                      className="text-slate-400 transition hover:text-red-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </li>
              );
            })}
            {inSprint.length === 0 && <li className="text-sm text-slate-400">Sin tareas todavía.</li>}
          </ul>
        </div>

        {canEdit && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              Añadir tarea
            </p>
            <Select
              value=""
              onChange={(e) => {
                if (e.target.value) onAssign(Number(e.target.value), sprintId);
              }}
            >
              <option value="">Selecciona una tarea…</option>
              {unassigned.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </Select>
            {unassigned.length === 0 && (
              <p className="mt-1 text-xs text-slate-400">No hay tareas sin asignar.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function SprintsPanel({
  projectId,
  canEdit,
}: {
  projectId: number;
  canEdit: boolean;
}) {
  const queryClient = useQueryClient();
  const sprintsQuery = useQuery({
    queryKey: ["sprints", projectId],
    queryFn: () => listSprints(projectId),
  });
  const tasksQuery = useQuery({
    queryKey: ["project-tasks", projectId],
    queryFn: () => listProjectTasks(projectId),
  });

  const [selected, setSelected] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [start, setStart] = useState(todayISO());
  const [end, setEnd] = useState(plusDaysISO(14));

  const invalidate = (sprintId?: number) => {
    queryClient.invalidateQueries({ queryKey: ["sprints", projectId] });
    queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
    queryClient.invalidateQueries({ queryKey: ["analytics", projectId] });
    if (sprintId) queryClient.invalidateQueries({ queryKey: ["burndown", sprintId] });
  };

  const createMut = useMutation({
    mutationFn: () =>
      createSprint(projectId, { name, goal: goal || null, start_date: start, end_date: end }),
    onSuccess: () => {
      invalidate();
      setShowForm(false);
      setName("");
      setGoal("");
    },
  });
  const statusMut = useMutation({
    mutationFn: ({ id, status }: { id: number; status: SprintStatus }) =>
      updateSprint(id, { status }),
    onSuccess: (_data, vars) => invalidate(vars.id),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteSprint(id),
    onSuccess: () => {
      invalidate();
      setSelected(null);
    },
  });
  const assignMut = useMutation({
    mutationFn: ({ taskId, sprintId }: { taskId: number; sprintId: number | null }) =>
      updateTask(taskId, { sprint_id: sprintId }),
    onSuccess: (_data, vars) => invalidate(vars.sprintId ?? undefined),
  });

  if (sprintsQuery.isLoading) {
    return (
      <Card className="p-5">
        <Spinner label="Cargando sprints…" />
      </Card>
    );
  }

  const sprints = sprintsQuery.data ?? [];
  const tasks = tasksQuery.data ?? [];

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <CalendarRange className="h-4 w-4 text-slate-400" /> Sprints
        </h2>
        {canEdit && (
          <Button size="sm" variant="secondary" onClick={() => setShowForm((s) => !s)}>
            <Plus className="h-4 w-4" /> Nuevo sprint
          </Button>
        )}
      </div>

      {showForm && canEdit && (
        <div className="mb-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <Input label="Nombre" value={name} onChange={(e) => setName(e.target.value)} placeholder="Sprint 1" />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Inicio" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            <Input label="Fin" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
          <Input label="Objetivo (opcional)" value={goal} onChange={(e) => setGoal(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
              Cancelar
            </Button>
            <Button size="sm" onClick={() => createMut.mutate()} disabled={!name.trim() || createMut.isPending}>
              Crear
            </Button>
          </div>
        </div>
      )}

      {sprints.length === 0 ? (
        <p className="text-sm text-slate-500">
          Aún no hay sprints.{canEdit && " Crea el primero para planear entregas."}
        </p>
      ) : (
        <ul className="space-y-2">
          {sprints.map((s) => {
            const meta = SPRINT_STATUS[s.status] ?? { label: s.status, tone: "neutral" as const };
            const isOpen = selected === s.id;
            return (
              <li key={s.id} className="overflow-hidden rounded-lg border border-slate-200">
                <button
                  type="button"
                  onClick={() => setSelected(isOpen ? null : s.id)}
                  className="flex w-full items-center gap-3 p-3 text-left transition hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-slate-900">{s.name}</span>
                      <Badge tone={meta.tone}>{meta.label}</Badge>
                    </div>
                    <div className="text-xs text-slate-500">
                      {fmt(s.start_date)} – {fmt(s.end_date)} · {s.done}/{s.total} tareas
                    </div>
                  </div>
                  <div className="w-24 shrink-0">
                    <div className="h-1.5 rounded-full bg-slate-100">
                      <div
                        className="h-1.5 rounded-full bg-brand-500"
                        style={{ width: `${s.completion_pct}%` }}
                      />
                    </div>
                    <div className="mt-1 text-right text-xs text-slate-400">{s.completion_pct}%</div>
                  </div>
                </button>
                {isOpen && (
                  <SprintDetail
                    sprintId={s.id}
                    canEdit={canEdit}
                    status={s.status}
                    tasks={tasks}
                    onStatus={(status) => statusMut.mutate({ id: s.id, status })}
                    onDelete={() => {
                      if (window.confirm("¿Eliminar el sprint? Las tareas no se borran.")) {
                        deleteMut.mutate(s.id);
                      }
                    }}
                    onAssign={(taskId, sprintId) => assignMut.mutate({ taskId, sprintId })}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
