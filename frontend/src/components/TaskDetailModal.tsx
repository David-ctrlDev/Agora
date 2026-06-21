import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  TASK_PRIORITY,
  TASK_STATUS,
  type Task,
  type TaskPriority,
  type TaskUpdate,
  addComment,
  listComments,
  updateTask,
} from "../api/tasks";
import { type AppUser } from "../api/users";
import { Badge, Button, Modal, Select, Spinner, Textarea } from "./ui";

interface Props {
  task: Task;
  canEdit: boolean;
  users: AppUser[];
  onClose: () => void;
}

export default function TaskDetailModal({ task, canEdit, users, onClose }: Props) {
  const queryClient = useQueryClient();
  const commentsQuery = useQuery({
    queryKey: ["task", task.id, "comments"],
    queryFn: () => listComments(task.id),
  });
  const [comment, setComment] = useState("");
  const [description, setDescription] = useState(task.description ?? "");

  const invalidateTasks = () =>
    queryClient.invalidateQueries({ queryKey: ["project", task.project_id, "tasks"] });

  const addCommentMut = useMutation({
    mutationFn: () => addComment(task.id, comment.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["task", task.id, "comments"] });
      setComment("");
    },
  });
  const update = useMutation({
    mutationFn: (patch: TaskUpdate) => updateTask(task.id, patch),
    onSuccess: invalidateTasks,
  });

  return (
    <Modal open onClose={onClose} title={task.title}>
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={TASK_STATUS[task.status]?.tone ?? "neutral"}>
            {TASK_STATUS[task.status]?.label ?? task.status}
          </Badge>
          <Badge tone={TASK_PRIORITY[task.priority]?.tone ?? "neutral"}>
            {TASK_PRIORITY[task.priority]?.label ?? task.priority}
          </Badge>
          {task.due_date && (
            <span className="text-xs text-slate-400">
              Vence {new Date(task.due_date).toLocaleDateString("es-CO")}
            </span>
          )}
        </div>

        {canEdit ? (
          <div className="space-y-3">
            <Textarea
              label="Descripción"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detalles de la tarea"
            />
            <div className="flex justify-end">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => update.mutate({ description: description || null })}
                disabled={update.isPending}
              >
                Guardar descripción
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Prioridad"
                value={task.priority}
                onChange={(e) => update.mutate({ priority: e.target.value as TaskPriority })}
              >
                {Object.entries(TASK_PRIORITY).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value.label}
                  </option>
                ))}
              </Select>
              <Select
                label="Responsable"
                value={task.assignee_id ?? ""}
                onChange={(e) =>
                  update.mutate({ assignee_id: e.target.value ? Number(e.target.value) : null })
                }
              >
                <option value="">Sin asignar</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-600">{task.description || "Sin descripción."}</p>
        )}

        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Comentarios</h3>
          {commentsQuery.isLoading ? (
            <Spinner label="Cargando…" />
          ) : (
            <ul className="space-y-3">
              {commentsQuery.data?.map((c) => (
                <li key={c.id} className="rounded-lg bg-slate-50 p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">
                      {c.author_name ?? "—"}
                    </span>
                    <span className="text-xs text-slate-400">
                      {new Date(c.created_at).toLocaleString("es-CO")}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-slate-700">{c.body}</p>
                </li>
              ))}
              {commentsQuery.data?.length === 0 && (
                <p className="text-sm text-slate-400">Sin comentarios todavía.</p>
              )}
            </ul>
          )}
          {canEdit && (
            <div className="mt-3 space-y-2">
              <Textarea
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Escribe un comentario…"
              />
              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={() => {
                    if (comment.trim()) addCommentMut.mutate();
                  }}
                  disabled={!comment.trim() || addCommentMut.isPending}
                >
                  Comentar
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
