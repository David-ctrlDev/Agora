import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { HEALTH, getOverview } from "../api/analytics";
import { ProgressRing } from "../components/charts";
import { Badge, Card, PageHeader, Spinner } from "../components/ui";

function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  hint?: string;
  tone?: "neutral" | "danger";
}) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div
        className={`mt-1 text-2xl font-semibold ${tone === "danger" ? "text-red-600" : "text-slate-900"}`}
      >
        {value}
      </div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </Card>
  );
}

export default function AnalyticsPage() {
  const query = useQuery({ queryKey: ["overview"], queryFn: getOverview });

  if (query.isLoading) return <Spinner label="Cargando analítica…" />;
  if (!query.data) return null;

  const { projects, totals } = query.data;

  return (
    <div className="space-y-6">
      <PageHeader title="Analítica" description="Avance y salud de tus proyectos" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Proyectos" value={totals.projects} hint={`${totals.active_projects} activos`} />
        <KpiCard
          label="Avance global"
          value={`${totals.completion_pct}%`}
          hint={`${totals.done_tasks}/${totals.total_tasks} tareas`}
        />
        <KpiCard
          label="Tareas vencidas"
          value={totals.overdue_tasks}
          tone={totals.overdue_tasks ? "danger" : "neutral"}
        />
        <KpiCard
          label="En riesgo"
          value={totals.at_risk_projects}
          tone={totals.at_risk_projects ? "danger" : "neutral"}
        />
      </div>

      {projects.length === 0 ? (
        <p className="text-sm text-slate-500">Aún no hay proyectos en tus áreas.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => {
            const health = HEALTH[p.health] ?? { label: p.health, tone: "neutral" as const };
            return (
              <Link key={p.project_id} to={`/proyectos/${p.project_id}`}>
                <Card className="p-5 transition hover:shadow-md">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="truncate font-medium text-slate-900">{p.name}</h3>
                    <Badge tone={health.tone}>{health.label}</Badge>
                  </div>
                  <div className="mt-4 flex items-center gap-4">
                    <ProgressRing value={p.completion_pct} size={72} thickness={9} />
                    <div className="space-y-0.5 text-sm text-slate-600">
                      <div>
                        {p.done}/{p.total} tareas
                      </div>
                      {p.overdue > 0 && <div className="text-red-600">{p.overdue} vencidas</div>}
                      {p.blocked > 0 && <div className="text-amber-600">{p.blocked} bloqueadas</div>}
                      {p.due_in_days != null && (
                        <div className="text-slate-500">
                          {p.due_in_days < 0
                            ? `${-p.due_in_days}d de retraso`
                            : `entrega en ${p.due_in_days}d`}
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
