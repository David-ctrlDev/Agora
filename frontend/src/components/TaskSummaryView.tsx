import { AlertTriangle, ListChecks } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { TASK_PRIORITY, TASK_STATUS, type TaskGroupStat, type TaskSummary } from "../api/tasks";
import { Badge, Card, Kpi, Panel, Select } from "./ui";

function GroupList({ items }: { items: TaskGroupStat[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">Sin datos.</p>;
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <div className="space-y-2.5">
      {items.map((g) => (
        <div key={g.key}>
          <div className="mb-1 flex items-center justify-between gap-2 text-xs">
            <span className="truncate text-slate-600">{g.key}</span>
            <span className="shrink-0 tabular-nums text-slate-400">
              {g.count}
              {g.overdue > 0 && <span className="text-red-500"> · {g.overdue} venc.</span>}
            </span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full bg-brand-500"
              style={{ width: `${(g.count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString("es-CO", { day: "2-digit", month: "short" }) : "—";

/** Resumen de tareas: KPIs, desglose por responsable/área y tabla filtrable. */
export function TaskSummaryView({ data }: { data: TaskSummary }) {
  const [fAssignee, setFAssignee] = useState("");
  const [fArea, setFArea] = useState("");
  const [fStatus, setFStatus] = useState("");

  const rows = useMemo(
    () =>
      data.items.filter(
        (t) =>
          (!fAssignee || (t.assignee_name ?? "Sin asignar") === fAssignee) &&
          (!fArea || t.area_name === fArea) &&
          (!fStatus || t.status === fStatus),
      ),
    [data.items, fAssignee, fArea, fStatus],
  );

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Tareas" value={data.total} hint={`${data.open} abiertas`} icon={<ListChecks className="h-4 w-4" />} tone="brand" />
        <Kpi label="Hechas" value={data.done} hint={`de ${data.total}`} tone="emerald" />
        <Kpi label="Vencidas" value={data.overdue} hint={data.overdue ? "requieren acción" : "al día"} icon={<AlertTriangle className="h-4 w-4" />} tone={data.overdue ? "red" : "slate"} />
        <Kpi label="Sin asignar" value={data.unassigned} hint={data.unassigned ? "por asignar" : "todo asignado"} tone={data.unassigned ? "red" : "slate"} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Por responsable">
          <GroupList items={data.by_assignee} />
        </Panel>
        <Panel title="Por área">
          <GroupList items={data.by_area} />
        </Panel>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4">
          <div className="w-44">
            <Select label="Responsable" value={fAssignee} onChange={(e) => setFAssignee(e.target.value)}>
              <option value="">Todos</option>
              {data.by_assignee.map((g) => (
                <option key={g.key} value={g.key}>{g.key}</option>
              ))}
            </Select>
          </div>
          <div className="w-40">
            <Select label="Área" value={fArea} onChange={(e) => setFArea(e.target.value)}>
              <option value="">Todas</option>
              {data.by_area.map((g) => (
                <option key={g.key} value={g.key}>{g.key}</option>
              ))}
            </Select>
          </div>
          <div className="w-40">
            <Select label="Estado" value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
              <option value="">Todos</option>
              {Object.entries(TASK_STATUS).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </Select>
          </div>
          <span className="mb-1.5 ml-auto text-xs text-slate-400">
            {rows.length} de {data.total} tareas
          </span>
        </div>
        <div className="max-h-[60vh] overflow-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2.5">Tarea</th>
                <th className="px-4 py-2.5">Responsable</th>
                <th className="px-4 py-2.5">Proyecto</th>
                <th className="px-4 py-2.5">Área</th>
                <th className="px-4 py-2.5">Estado</th>
                <th className="px-4 py-2.5">Prioridad</th>
                <th className="px-4 py-2.5">Entrega</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-sm text-slate-400">
                    Ninguna tarea coincide con los filtros.
                  </td>
                </tr>
              ) : (
                rows.map((t) => {
                  const st = TASK_STATUS[t.status] ?? { label: t.status, tone: "neutral" as const };
                  const prio = TASK_PRIORITY[t.priority] ?? { label: t.priority, tone: "neutral" as const };
                  return (
                    <tr key={t.id} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5">
                        <Link to={`/proyectos/${t.project_id}`} className="max-w-[260px] truncate font-medium text-slate-800 hover:text-brand-600" title={t.title}>
                          {t.title}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 text-slate-600">{t.assignee_name ?? <span className="text-slate-300">Sin asignar</span>}</td>
                      <td className="px-4 py-2.5 text-slate-500">{t.project_name}</td>
                      <td className="px-4 py-2.5 text-slate-500">{t.area_name}</td>
                      <td className="px-4 py-2.5"><Badge tone={st.tone}>{st.label}</Badge></td>
                      <td className="px-4 py-2.5"><Badge tone={prio.tone}>{prio.label}</Badge></td>
                      <td className={`whitespace-nowrap px-4 py-2.5 text-xs ${t.overdue ? "font-semibold text-red-600" : "text-slate-500"}`}>
                        {fmtDate(t.due_date)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
