import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  FolderKanban,
  ListChecks,
  type LucideIcon,
} from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { STATUS_META, getOverview } from "../api/analytics";
import { listNotifications } from "../api/notifications";
import { PROJECT_STATUS, listProjects } from "../api/projects";
import { TASK_PRIORITY, listMyTasks } from "../api/tasks";
import { useMe } from "../auth/useAuth";
import { BarList, Donut, ProgressRing } from "../components/charts";
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

const PROJECT_COLOR: Record<string, string> = {
  planned: "#94a3b8",
  active: "#6366f1",
  on_hold: "#f59e0b",
  done: "#10b981",
  archived: "#cbd5e1",
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

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="mb-4 text-sm font-semibold text-slate-700">{title}</h2>
      {children}
    </Card>
  );
}

export default function HomePage() {
  const me = useMe();
  const overview = useQuery({ queryKey: ["overview"], queryFn: getOverview });
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const myTasks = useQuery({ queryKey: ["my-tasks"], queryFn: listMyTasks });
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: listNotifications });

  const totals = overview.data?.totals;
  const oProjects = overview.data?.projects ?? [];
  const allProjects = projectsQuery.data ?? [];
  const tasks = myTasks.data ?? [];
  const alerts = (notifications.data ?? []).filter((n) => n.status === "unread");

  const firstName = (me.data?.name ?? "").split(" ")[0];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const projectsByStatus = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const p of oProjects) counts[p.status] = (counts[p.status] ?? 0) + 1;
    return Object.entries(counts).map(([s, v]) => ({
      label: PROJECT_STATUS[s]?.label ?? s,
      value: v,
      color: PROJECT_COLOR[s] ?? "#cbd5e1",
    }));
  }, [oProjects]);

  const tasksByStatus = useMemo(() => {
    const agg: Record<string, number> = {};
    for (const p of oProjects)
      for (const [s, n] of Object.entries(p.by_status ?? {})) agg[s] = (agg[s] ?? 0) + n;
    return Object.entries(agg)
      .filter(([, v]) => v > 0)
      .map(([s, v]) => ({
        label: STATUS_META[s]?.label ?? s,
        value: v,
        color: STATUS_META[s]?.color ?? "#cbd5e1",
      }));
  }, [oProjects]);

  const byArea = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const p of allProjects) {
      const a = p.area_name ?? "—";
      counts[a] = (counts[a] ?? 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([a, v]) => ({ label: a, value: v, color: "#6366f1" }));
  }, [allProjects]);

  const loading = overview.isLoading || projectsQuery.isLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title={firstName ? `Hola, ${firstName}` : "Inicio"}
        description="Resumen de tu trabajo y tu cartera de proyectos."
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

      {loading ? (
        <Spinner label="Cargando resumen…" />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <ChartCard title="Avance global">
              <div className="flex items-center gap-4">
                <ProgressRing value={totals?.completion_pct ?? 0} />
                <div className="text-sm text-slate-600">
                  <div className="text-2xl font-semibold text-slate-900">
                    {totals?.completion_pct ?? 0}%
                  </div>
                  <div>
                    {totals?.done_tasks ?? 0}/{totals?.total_tasks ?? 0} tareas
                  </div>
                  {(totals?.active_projects ?? 0) > 0 && (
                    <div className="mt-1 text-xs text-slate-400">
                      {totals?.active_projects} proyectos activos
                    </div>
                  )}
                </div>
              </div>
            </ChartCard>

            <ChartCard title="Proyectos por estado">
              {projectsByStatus.length > 0 ? (
                <Donut
                  segments={projectsByStatus}
                  centerValue={String(totals?.projects ?? 0)}
                  centerLabel="proyectos"
                />
              ) : (
                <p className="text-sm text-slate-400">Sin proyectos.</p>
              )}
            </ChartCard>

            <ChartCard title="Tareas por estado">
              {tasksByStatus.length > 0 ? (
                <Donut
                  segments={tasksByStatus}
                  centerValue={String(totals?.total_tasks ?? 0)}
                  centerLabel="tareas"
                />
              ) : (
                <p className="text-sm text-slate-400">Sin tareas.</p>
              )}
            </ChartCard>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Proyectos por área">
              {byArea.length > 0 ? (
                <BarList items={byArea} />
              ) : (
                <p className="text-sm text-slate-400">Sin datos.</p>
              )}
            </ChartCard>

            <Card className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-700">Alertas</h2>
                <Link to="/notificaciones" className="text-xs text-brand-600 hover:underline">
                  Ver todas
                </Link>
              </div>
              {alerts.length === 0 ? (
                <p className="text-sm text-slate-400">Sin alertas. Todo en orden.</p>
              ) : (
                <ul className="space-y-3">
                  {alerts.slice(0, 5).map((n) => (
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
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">Mis tareas</h2>
              <Link to="/tareas" className="text-xs text-brand-600 hover:underline">
                Ver todas
              </Link>
            </div>
            {tasks.length === 0 ? (
              <p className="flex items-center gap-2 text-sm text-slate-400">
                <CheckCircle2 className="h-4 w-4" /> Sin tareas pendientes. 🎉
              </p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {tasks.slice(0, 8).map((t) => {
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
        </>
      )}
    </div>
  );
}
