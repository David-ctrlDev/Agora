import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  FolderKanban,
  ListChecks,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { HEALTH, getOverview } from "../api/analytics";
import { listNotifications } from "../api/notifications";
import { TASK_PRIORITY, listMyTasks } from "../api/tasks";
import { useMe } from "../auth/useAuth";
import { ProgressRing } from "../components/charts";
import { Badge, Card, PageHeader, Spinner } from "../components/ui";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

const SEVERITY: Record<string, Tone> = {
  info: "brand",
  low: "neutral",
  medium: "warning",
  high: "danger",
  warning: "warning",
  critical: "danger",
};

function Kpi({
  icon: Icon,
  label,
  value,
  tone = "neutral",
  to,
}: {
  icon: LucideIcon;
  label: string;
  value: number | string;
  tone?: "neutral" | "danger" | "warning";
  to?: string;
}) {
  const valueColor =
    tone === "danger" ? "text-red-600" : tone === "warning" ? "text-amber-600" : "text-slate-900";
  const inner = (
    <Card className="flex items-center gap-3 p-4 transition hover:shadow-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className={`text-2xl font-semibold ${valueColor}`}>{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </Card>
  );
  return to ? (
    <Link to={to} className="block">
      {inner}
    </Link>
  ) : (
    inner
  );
}

export default function HomePage() {
  const me = useMe();
  const overview = useQuery({ queryKey: ["overview"], queryFn: getOverview });
  const myTasks = useQuery({ queryKey: ["my-tasks"], queryFn: listMyTasks });
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: listNotifications });

  const totals = overview.data?.totals;
  const projects = overview.data?.projects ?? [];
  const tasks = myTasks.data ?? [];
  const alerts = (notifications.data ?? []).filter((n) => n.status === "unread");

  const firstName = (me.data?.name ?? "").split(" ")[0];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title={firstName ? `Hola, ${firstName}` : "Inicio"}
        description="Este es el resumen de tu trabajo."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon={FolderKanban} label="Proyectos" value={totals?.projects ?? "—"} to="/proyectos" />
        <Kpi icon={ListChecks} label="Mis tareas" value={tasks.length} to="/tareas" />
        <Kpi
          icon={AlertTriangle}
          label="Tareas vencidas"
          value={totals?.overdue_tasks ?? 0}
          tone={(totals?.overdue_tasks ?? 0) > 0 ? "danger" : "neutral"}
          to="/tareas"
        />
        <Kpi
          icon={Bell}
          label="Alertas"
          value={alerts.length}
          tone={alerts.length > 0 ? "warning" : "neutral"}
          to="/notificaciones"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Mis tareas</h2>
            <Link to="/tareas" className="text-xs text-brand-600 hover:underline">
              Ver todas
            </Link>
          </div>
          {myTasks.isLoading ? (
            <Spinner label="Cargando…" />
          ) : tasks.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-slate-400">
              <CheckCircle2 className="h-4 w-4" /> Sin tareas pendientes. 🎉
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {tasks.slice(0, 6).map((t) => {
                const prio = TASK_PRIORITY[t.priority] ?? { label: t.priority, tone: "neutral" as const };
                const overdue = t.due_date != null && new Date(t.due_date) < today;
                return (
                  <li key={t.id}>
                    <Link
                      to={`/proyectos/${t.project_id}`}
                      className="flex items-center justify-between gap-3 py-2 text-sm transition hover:text-brand-700"
                    >
                      <div className="min-w-0">
                        <div className="truncate font-medium text-slate-800">{t.title}</div>
                        <div className="truncate text-xs text-slate-400">
                          {t.project_name}
                          {t.due_date && ` · vence ${new Date(t.due_date).toLocaleDateString("es-CO")}`}
                        </div>
                      </div>
                      <Badge tone={overdue ? "danger" : prio.tone}>
                        {overdue ? "Vencida" : prio.label}
                      </Badge>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Alertas</h2>
            <Link to="/notificaciones" className="text-xs text-brand-600 hover:underline">
              Ver todas
            </Link>
          </div>
          {notifications.isLoading ? (
            <Spinner label="Cargando…" />
          ) : alerts.length === 0 ? (
            <p className="text-sm text-slate-400">Sin alertas. Todo en orden.</p>
          ) : (
            <ul className="space-y-3">
              {alerts.slice(0, 6).map((n) => (
                <li key={n.id} className="flex gap-3 text-sm">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-slate-800">{n.title}</div>
                    <div className="truncate text-xs text-slate-500">{n.body}</div>
                  </div>
                  <Badge tone={SEVERITY[n.severity] ?? "neutral"}>{n.severity}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Tus proyectos</h2>
          <Link to="/analitica" className="text-xs text-brand-600 hover:underline">
            Ver analítica
          </Link>
        </div>
        {overview.isLoading ? (
          <Spinner label="Cargando…" />
        ) : projects.length === 0 ? (
          <p className="text-sm text-slate-400">Aún no tienes proyectos en tus áreas.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.slice(0, 6).map((p) => {
              const health = HEALTH[p.health] ?? { label: p.health, tone: "neutral" as const };
              return (
                <Link key={p.project_id} to={`/proyectos/${p.project_id}`}>
                  <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-4 transition hover:shadow-sm">
                    <ProgressRing value={p.completion_pct} size={56} thickness={7} />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-slate-900">{p.name}</div>
                      <div className="mt-1">
                        <Badge tone={health.tone}>{health.label}</Badge>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
