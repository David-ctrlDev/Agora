import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  TASK_PRIORITY,
  TASK_STATUS,
  TASK_STATUS_ORDER,
  type Task,
  type TaskCreate,
  type TaskPriority,
  type TaskStatus,
  createTask,
  deleteTask,
  listProjectTasks,
  updateTask,
} from "../api/tasks";
import { type AppUser } from "../api/users";
import TaskDetailModal from "./TaskDetailModal";
import { Badge, Button, Card, Input, Select, Spinner } from "./ui";

interface Props {
  projectId: number;
  canEdit: boolean;
  /** Puede aprobar (pasar a Hecha / sacar de Aprobación): líder, admin de área o super admin. */
  canApprove?: boolean;
  /** Tablero de AJUSTES (post-entrega): tareas aparte que no afectan el avance. */
  adjustments?: boolean;
  title?: string;
  users: AppUser[];
}

export default function TasksBoard({
  projectId,
  canEdit,
  canApprove = false,
  adjustments = false,
  title: boardTitle = "Tareas",
  users,
}: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["project", projectId, "tasks", adjustments];
  const tasksQuery = useQuery({
    queryKey,
    queryFn: () => listProjectTasks(projectId, adjustments),
  });

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [assigneeId, setAssigneeId] = useState<number | "">("");
  const [dueDate, setDueDate] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);
  const [overCol, setOverCol] = useState<TaskStatus | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey });
  const create = useMutation({
    mutationFn: (payload: TaskCreate) => createTask(projectId, payload),
    onSuccess: () => {
      void invalidate();
      setTitle("");
      setPriority("medium");
      setAssigneeId("");
      setDueDate("");
      setShowForm(false);
    },
  });
  const update = useMutation({
    mutationFn: ({ id, status }: { id: number; status: TaskStatus }) => updateTask(id, { status }),
    // Movimiento optimista: la tarjeta salta de columna al instante (clave para el drag&drop).
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey });
      const prev = queryClient.getQueryData<Task[]>(queryKey);
      queryClient.setQueryData<Task[]>(queryKey, (old) =>
        old?.map((t) => (t.id === id ? { ...t, status } : t)),
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(queryKey, ctx.prev);
    },
    onSettled: () => invalidate(),
  });
  const remove = useMutation({ mutationFn: (id: number) => deleteTask(id), onSuccess: invalidate });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    create.mutate({
      title: title.trim(),
      priority,
      assignee_id: assigneeId === "" ? null : Number(assigneeId),
      due_date: dueDate || null,
      is_adjustment: adjustments,
    });
  };

  const tasks = tasksQuery.data ?? [];
  const selectedTask = tasks.find((t) => t.id === selectedId) ?? null;

  // Flujo de aprobación: sin permiso de aprobar no se puede pasar a "Hecha" ni
  // mover una tarea que ya está en Aprobación (el backend también lo valida).
  const canMove = (task: Task, target: TaskStatus) => {
    if (canApprove) return true;
    if (task.status === "approval") return false;
    return target !== "done";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{boardTitle}</h2>
          {adjustments && (
            <p className="text-xs text-slate-400">
              Trabajo post-entrega: no afecta el avance del proyecto (métrica aparte).
            </p>
          )}
        </div>
        {canEdit && (
          <Button
            size="sm"
            variant={showForm ? "secondary" : "primary"}
            onClick={() => setShowForm((v) => !v)}
          >
            <Plus className="h-4 w-4" /> {adjustments ? "Nuevo ajuste" : "Nueva tarea"}
          </Button>
        )}
      </div>

      {canEdit && showForm && (
        <Card className="p-4">
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:items-end">
            <div className="sm:col-span-2">
              <Input
                label="Título"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="¿Qué hay que hacer?"
                maxLength={300}
              />
            </div>
            <Select
              label="Prioridad"
              value={priority}
              onChange={(e) => setPriority(e.target.value as TaskPriority)}
            >
              {Object.entries(TASK_PRIORITY).map(([key, value]) => (
                <option key={key} value={key}>
                  {value.label}
                </option>
              ))}
            </Select>
            <Select
              label="Responsable"
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Sin asignar</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </Select>
            <Input
              label="Vence"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
            <div className="flex justify-end sm:col-span-2 lg:col-span-4">
              <Button type="submit" disabled={!title.trim() || create.isPending}>
                {create.isPending ? "Creando…" : "Crear tarea"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {tasksQuery.isLoading ? (
        <Spinner label="Cargando tareas…" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {TASK_STATUS_ORDER.map((statusKey) => {
            const column = tasks.filter((t) => t.status === statusKey);
            const meta = TASK_STATUS[statusKey];
            return (
              <div
                key={statusKey}
                onDragOver={(e) => {
                  const dragged = tasks.find((t) => t.id === dragId);
                  if (canEdit && dragged && canMove(dragged, statusKey)) {
                    e.preventDefault();
                    setOverCol(statusKey);
                  }
                }}
                onDragLeave={(e) => {
                  if (e.currentTarget === e.target) {
                    setOverCol((c) => (c === statusKey ? null : c));
                  }
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  const id = dragId ?? Number(e.dataTransfer.getData("text/plain"));
                  setOverCol(null);
                  setDragId(null);
                  const dragged = tasks.find((t) => t.id === id);
                  if (id && dragged && dragged.status !== statusKey && canMove(dragged, statusKey)) {
                    update.mutate({ id, status: statusKey });
                  }
                }}
                className={`rounded-xl p-3 transition ${
                  overCol === statusKey
                    ? "bg-brand-50 ring-2 ring-brand-300"
                    : "bg-slate-100/70"
                }`}
              >
                <div className="mb-3 flex items-center justify-between px-1">
                  <span className="text-sm font-semibold text-slate-700">{meta.label}</span>
                  <span className="text-xs text-slate-400">{column.length}</span>
                </div>
                <div className="space-y-2">
                  {column.map((t) => (
                    <Card
                      key={t.id}
                      draggable={canEdit}
                      onDragStart={(e) => {
                        setDragId(t.id);
                        e.dataTransfer.effectAllowed = "move";
                        e.dataTransfer.setData("text/plain", String(t.id));
                      }}
                      onDragEnd={() => {
                        setDragId(null);
                        setOverCol(null);
                      }}
                      className={`p-3 ${canEdit ? "cursor-grab active:cursor-grabbing" : ""} ${
                        dragId === t.id ? "opacity-50" : ""
                      }`}
                    >
                      <div className="mb-2 flex items-start justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedId(t.id)}
                          className="text-left text-sm font-medium text-slate-900 hover:text-brand-600"
                        >
                          {t.title}
                        </button>
                        <Badge tone={TASK_PRIORITY[t.priority]?.tone ?? "neutral"}>
                          {TASK_PRIORITY[t.priority]?.label ?? t.priority}
                        </Badge>
                      </div>
                      <div className="mb-2 flex flex-wrap gap-x-2 text-xs text-slate-400">
                        {t.assignee_name && <span>{t.assignee_name}</span>}
                        {t.due_date && (
                          <span>· {new Date(t.due_date).toLocaleDateString("es-CO")}</span>
                        )}
                      </div>
                      {canEdit && (
                        <div className="flex items-center gap-2">
                          {t.status === "approval" && !canApprove ? (
                            <span className="flex-1 text-xs italic text-amber-600">
                              Esperando aprobación del líder
                            </span>
                          ) : (
                            <select
                              value={t.status}
                              onChange={(e) =>
                                update.mutate({ id: t.id, status: e.target.value as TaskStatus })
                              }
                              className="h-7 flex-1 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700 focus:border-brand-500 focus:outline-none"
                            >
                              {TASK_STATUS_ORDER.filter(
                                (st) => st === t.status || canMove(t, st),
                              ).map((st) => (
                                <option key={st} value={st}>
                                  {st === "approval" && !canApprove
                                    ? "Enviar a aprobación"
                                    : TASK_STATUS[st].label}
                                </option>
                              ))}
                            </select>
                          )}
                          <button
                            type="button"
                            onClick={() => remove.mutate(t.id)}
                            title="Eliminar"
                            className="rounded p-1 text-slate-300 transition hover:bg-slate-100 hover:text-red-600"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </Card>
                  ))}
                  {column.length === 0 && (
                    <p className="px-1 py-3 text-center text-xs text-slate-300">—</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedTask && (
        <TaskDetailModal
          key={selectedTask.id}
          task={selectedTask}
          canEdit={canEdit}
          users={users}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
