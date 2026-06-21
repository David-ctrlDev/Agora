import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { TASK_PRIORITY, TASK_STATUS, type Task, listMyTasks } from "../api/tasks";
import { Badge, Card, PageHeader, Spinner } from "../components/ui";

export default function TasksPage() {
  const tasksQuery = useQuery({ queryKey: ["my-tasks"], queryFn: listMyTasks });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Mis tareas"
        description="Tareas asignadas a ti, pendientes, ordenadas por fecha de entrega."
      />

      {tasksQuery.isLoading && <Spinner label="Cargando…" />}
      {tasksQuery.data?.length === 0 && (
        <Card className="p-8 text-center text-sm text-slate-500">
          No tienes tareas pendientes. 🎉
        </Card>
      )}
      {tasksQuery.data && tasksQuery.data.length > 0 && (
        <Card className="divide-y divide-slate-100">
          {tasksQuery.data.map((t: Task) => (
            <Link
              key={t.id}
              to={`/proyectos/${t.project_id}`}
              className="flex items-center justify-between gap-3 p-4 transition hover:bg-slate-50"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-900">{t.title}</div>
                <div className="text-xs text-slate-500">{t.project_name}</div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {t.due_date && (
                  <span className="text-xs text-slate-400">
                    {new Date(t.due_date).toLocaleDateString("es-CO")}
                  </span>
                )}
                <Badge tone={TASK_PRIORITY[t.priority]?.tone ?? "neutral"}>
                  {TASK_PRIORITY[t.priority]?.label ?? t.priority}
                </Badge>
                <Badge tone={TASK_STATUS[t.status]?.tone ?? "neutral"}>
                  {TASK_STATUS[t.status]?.label ?? t.status}
                </Badge>
              </div>
            </Link>
          ))}
        </Card>
      )}
    </div>
  );
}
