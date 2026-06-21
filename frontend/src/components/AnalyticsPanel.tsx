import { useQuery } from "@tanstack/react-query";

import { PRIORITY_META, STATUS_META, getProjectAnalytics, HEALTH } from "../api/analytics";
import { BarList, Donut, ProgressRing } from "./charts";
import { Badge, Card, Spinner } from "./ui";

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  tone?: "neutral" | "danger" | "warning";
}) {
  const color =
    tone === "danger" ? "text-red-600" : tone === "warning" ? "text-amber-600" : "text-slate-900";
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <div className={`text-lg font-semibold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

export default function AnalyticsPanel({ projectId }: { projectId: number }) {
  const query = useQuery({
    queryKey: ["analytics", projectId],
    queryFn: () => getProjectAnalytics(projectId),
  });

  if (query.isLoading) {
    return (
      <Card className="p-5">
        <Spinner label="Cargando analítica…" />
      </Card>
    );
  }
  if (!query.data) return null;

  const a = query.data;
  const health = HEALTH[a.health] ?? { label: a.health, tone: "neutral" as const };
  const statusSegments = Object.entries(a.by_status).map(([key, value]) => ({
    label: STATUS_META[key]?.label ?? key,
    value,
    color: STATUS_META[key]?.color ?? "#cbd5e1",
  }));
  const priorityItems = Object.entries(a.by_priority).map(([key, value]) => ({
    label: PRIORITY_META[key]?.label ?? key,
    value,
    color: PRIORITY_META[key]?.color ?? "#94a3b8",
  }));
  const dueValue =
    a.due_in_days == null
      ? "—"
      : a.due_in_days < 0
        ? `${-a.due_in_days}d tarde`
        : `${a.due_in_days}d`;

  return (
    <Card className="p-5">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Avance del proyecto</h2>
        <Badge tone={health.tone}>{health.label}</Badge>
      </div>

      <div className="grid items-center gap-6 sm:grid-cols-3">
        <div className="flex flex-col items-center">
          <ProgressRing value={a.completion_pct} />
          <p className="mt-2 text-xs text-slate-500">
            {a.done} de {a.total} tareas
          </p>
        </div>
        <div className="sm:col-span-2">
          {a.total > 0 ? (
            <Donut segments={statusSegments} centerValue={`${a.open}`} centerLabel="abiertas" />
          ) : (
            <p className="text-sm text-slate-500">Aún no hay tareas en este proyecto.</p>
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-5 border-t border-slate-100 pt-5 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            Por prioridad
          </p>
          <BarList items={priorityItems} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Vencidas" value={a.overdue} tone={a.overdue ? "danger" : "neutral"} />
          <Stat label="Bloqueadas" value={a.blocked} tone={a.blocked ? "warning" : "neutral"} />
          <Stat label="Entrega" value={dueValue} tone={a.due_in_days != null && a.due_in_days < 0 ? "danger" : "neutral"} />
          <Stat label="Completado" value={`${a.completion_pct}%`} />
        </div>
      </div>
    </Card>
  );
}
