import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CalendarClock,
  CheckCircle2,
  FolderKanban,
  TrendingUp,
} from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { CRITICALITY_META } from "../api/analytics";
import { listNotifications } from "../api/notifications";
import { PROJECT_STATUS, type Project, listProjects } from "../api/projects";
import { TASK_PRIORITY, listMyTasks } from "../api/tasks";
import { useMe } from "../auth/useAuth";
import { Donut, ProgressRing } from "../components/charts";
import { Badge, Card, Kpi, PageHeader, Panel, Spinner } from "../components/ui";

const PALETTE = ["#10b981", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6", "#6366f1", "#f97316"];
const PROJECT_COLOR: Record<string, string> = {
  planned: "#94a3b8",
  active: "#10b981",
  on_hold: "#f59e0b",
  done: "#047857",
  archived: "#cbd5e1",
};

function tally(items: Project[], pick: (p: Project) => string | null) {
  const m = new Map<string, number>();
  for (const p of items) {
    const k = (pick(p) ?? "").trim();
    if (k) m.set(k, (m.get(k) ?? 0) + 1);
  }
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

function MiniBars({ items }: { items: { label: string; value: number; color: string }[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">Sin datos.</p>;
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="space-y-2.5">
      {items.map((it) => (
        <div key={it.label}>
          <div className="mb-1 flex items-center justify-between gap-2 text-xs">
            <span className="truncate text-slate-600">{it.label}</span>
            <span className="shrink-0 tabular-nums text-slate-400">{it.value}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div className="h-2 rounded-full" style={{ width: `${(it.value / max) * 100}%`, background: it.color }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function dueLabel(due: string): { text: string; danger: boolean } {
  const days = Math.round((new Date(due).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return { text: `${-days}d tarde`, danger: true };
  if (days === 0) return { text: "hoy", danger: true };
  return { text: `en ${days}d`, danger: false };
}

export default function HomePage() {
  const me = useMe();
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const myTasks = useQuery({ queryKey: ["my-tasks"], queryFn: listMyTasks });
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: listNotifications });

  const allProjects = projectsQuery.data ?? [];
  const isAdmin = me.data?.role === "admin";
  // Admin: toda la cartera. Miembro: solo los proyectos que lidera.
  const projects = isAdmin ? allProjects : allProjects.filter((p) => p.owner_id === me.data?.id);
  const tasks = myTasks.data ?? [];
  const alerts = (notifications.data ?? []).filter((n) => n.status === "unread");
  const firstName = (me.data?.name ?? "").split(" ")[0];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const active = projects.filter((p) => p.status === "active").length;
  const doneCount = projects.filter((p) => p.status === "done").length;
  const avgProgress = projects.length
    ? Math.round(projects.reduce((s, p) => s + (p.progress ?? 0), 0) / projects.length)
    : 0;

  const byStatus = useMemo(
    () =>
      tally(projects, (p) => p.status).map(([s, v]) => ({
        label: PROJECT_STATUS[s]?.label ?? s,
        value: v,
        color: PROJECT_COLOR[s] ?? "#cbd5e1",
      })),
    [projects],
  );
  const byCrit = useMemo(
    () =>
      tally(projects, (p) => p.criticality || "Sin definir").map(([c, v]) => ({
        label: CRITICALITY_META[c]?.label ?? c,
        value: v,
        color: CRITICALITY_META[c]?.color ?? "#cbd5e1",
      })),
    [projects],
  );
  const byCategory = useMemo(
    () =>
      tally(projects, (p) => p.category)
        .slice(0, 7)
        .map(([c, v], i) => ({ label: c, value: v, color: PALETTE[i % PALETTE.length] })),
    [projects],
  );
  const upcoming = useMemo(
    () =>
      projects
        .filter((p) => p.due_date && p.status !== "done" && p.status !== "archived")
        .sort((a, b) => (a.due_date! < b.due_date! ? -1 : 1))
        .slice(0, 6),
    [projects],
  );
  const spotlight = useMemo(
    () =>
      projects
        .filter((p) => p.status === "active")
        .slice()
        .sort((a, b) => (b.progress ?? 0) - (a.progress ?? 0))
        .slice(0, 6),
    [projects],
  );

  if (projectsQuery.isLoading) return <Spinner label="Cargando resumen…" />;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={new Date().toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" })}
        title={firstName ? `Hola, ${firstName}` : "Inicio"}
        description={
          isAdmin ? "Resumen de toda la cartera de proyectos." : "Resumen de los proyectos que lideras."
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label={isAdmin ? "Proyectos" : "Mis proyectos"} value={projects.length} hint={`${active} en curso`} icon={<FolderKanban className="h-4 w-4" />} tone="brand" />
        <Kpi label="Avance promedio" value={`${avgProgress}%`} hint="de la cartera" icon={<TrendingUp className="h-4 w-4" />} tone="emerald" />
        <Kpi label="En curso" value={active} hint="proyectos activos" icon={<Activity className="h-4 w-4" />} tone="brand" />
        <Kpi label="Completados" value={doneCount} hint="proyectos terminados" icon={<CheckCircle2 className="h-4 w-4" />} tone="emerald" />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Avance promedio">
          <div className="flex items-center gap-5">
            <ProgressRing value={avgProgress} />
            <div className="text-sm text-slate-600">
              <div>
                <span className="font-semibold text-slate-900">{active}</span> en curso
              </div>
              <div>
                <span className="font-semibold text-slate-900">{doneCount}</span> completados
              </div>
              <div className="mt-1 text-xs text-slate-400">{projects.length} proyectos en total</div>
            </div>
          </div>
        </Panel>
        <Panel title="Proyectos por estado">
          {byStatus.length ? (
            <Donut segments={byStatus} centerValue={`${projects.length}`} centerLabel="proyectos" />
          ) : (
            <p className="text-sm text-slate-400">Sin proyectos.</p>
          )}
        </Panel>
        <Panel title="Criticidad">
          {byCrit.length ? (
            <Donut segments={byCrit} centerValue={`${projects.length}`} centerLabel="proyectos" />
          ) : (
            <p className="text-sm text-slate-400">Sin datos.</p>
          )}
        </Panel>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Proyectos por categoría">
          <MiniBars items={byCategory} />
        </Panel>
        <Panel
          title="Próximas entregas"
          actions={<Link to="/proyectos" className="text-xs font-medium text-brand-600 hover:underline">Ver proyectos</Link>}
        >
          {upcoming.length === 0 ? (
            <p className="text-sm text-slate-400">Sin fechas de entrega próximas.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {upcoming.map((p) => {
                const d = dueLabel(p.due_date!);
                return (
                  <li key={p.id}>
                    <Link to={`/proyectos/${p.id}`} className="flex items-center justify-between gap-3 py-2 transition hover:text-brand-700">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-slate-800">{p.name}</div>
                        <div className="truncate text-xs text-slate-400">
                          {new Date(p.due_date!).toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "2-digit" })}
                          {p.owner_name ? ` · ${p.owner_name}` : ""}
                        </div>
                      </div>
                      <Badge tone={d.danger ? "danger" : "neutral"}>{d.text}</Badge>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Proyectos activos destacados" subtitle="Mayor avance">
          {spotlight.length === 0 ? (
            <p className="text-sm text-slate-400">Sin proyectos activos.</p>
          ) : (
            <ul className="space-y-2.5">
              {spotlight.map((p) => (
                <li key={p.id}>
                  <Link to={`/proyectos/${p.id}`} className="flex items-center gap-3 rounded-lg px-1 py-0.5 transition hover:bg-slate-50">
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-700">{p.name}</span>
                    <div className="h-1.5 w-24 shrink-0 rounded-full bg-slate-100">
                      <div className="h-1.5 rounded-full bg-brand-500" style={{ width: `${Math.max(p.progress ?? 0, 1)}%` }} />
                    </div>
                    <span className="w-9 shrink-0 text-right text-xs tabular-nums text-slate-500">{p.progress ?? 0}%</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Mis tareas"
          actions={<Link to="/tareas" className="text-xs font-medium text-brand-600 hover:underline">Ver todas</Link>}
        >
          {tasks.length === 0 ? (
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
                    <Link to={`/proyectos/${t.project_id}`} className="flex items-center justify-between gap-3 py-2 text-sm transition hover:text-brand-700">
                      <div className="min-w-0">
                        <div className="truncate font-medium text-slate-800">{t.title}</div>
                        <div className="truncate text-xs text-slate-400">{t.project_name}</div>
                      </div>
                      <Badge tone={overdue ? "danger" : prio.tone}>{overdue ? "Vencida" : prio.label}</Badge>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>
      </div>

      {alerts.length > 0 && (
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <CalendarClock className="h-4 w-4 text-amber-500" /> Alertas
            </h2>
            <Link to="/notificaciones" className="text-xs font-medium text-brand-600 hover:underline">Ver todas</Link>
          </div>
          <ul className="space-y-3">
            {alerts.slice(0, 5).map((n) => (
              <li key={n.id} className="flex gap-3 text-sm">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-slate-800">{n.title}</div>
                  <div className="truncate text-xs text-slate-500">{n.body}</div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
