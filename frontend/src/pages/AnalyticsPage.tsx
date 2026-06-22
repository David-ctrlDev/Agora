import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  FolderKanban,
  ShieldAlert,
  TrendingUp,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  CRITICALITY_META,
  HEALTH,
  PRIORITY_META,
  PROJECT_STATUS_META,
  STATUS_META,
  type ProjectAnalytics,
  getOverview,
} from "../api/analytics";
import { Donut } from "../components/charts";
import { Badge, Kpi, PageHeader, Panel, Select, Spinner } from "../components/ui";

type Meta = Record<string, { label: string; color: string }>;
const PALETTE = [
  "#10b981", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6",
  "#6366f1", "#f97316", "#64748b", "#ec4899", "#22c55e", "#eab308",
];
const BUCKET_COLORS = ["#ef4444", "#f59e0b", "#0ea5e9", "#10b981"];

interface Item {
  label: string;
  value: number;
  color: string;
}

function tally(items: ProjectAnalytics[], pick: (p: ProjectAnalytics) => string | null | undefined) {
  const m = new Map<string, number>();
  for (const p of items) {
    const k = (pick(p) ?? "").trim();
    if (k) m.set(k, (m.get(k) ?? 0) + 1);
  }
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

function segments(entries: [string, number][], meta?: Meta): Item[] {
  return entries.map(([k, v], i) => ({
    label: meta?.[k]?.label ?? k,
    value: v,
    color: meta?.[k]?.color ?? PALETTE[i % PALETTE.length],
  }));
}

function topN(entries: [string, number][], n: number): [string, number][] {
  if (entries.length <= n) return entries;
  const rest = entries.slice(n).reduce((s, [, v]) => s + v, 0);
  return [...entries.slice(0, n), ["Otros", rest]];
}

function sumDict(items: ProjectAnalytics[], field: "by_status" | "by_priority") {
  const m: Record<string, number> = {};
  for (const p of items) for (const [k, v] of Object.entries(p[field])) m[k] = (m[k] ?? 0) + v;
  return m;
}

function dictToItems(rec: Record<string, number>, meta: Meta): Item[] {
  return Object.entries(rec)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ label: meta[k]?.label ?? k, value: v, color: meta[k]?.color ?? "#cbd5e1" }))
    .sort((a, b) => b.value - a.value);
}

function uniques(items: ProjectAnalytics[], pick: (p: ProjectAnalytics) => string | null) {
  return [...new Set(items.map((p) => (pick(p) ?? "").trim()).filter(Boolean))].sort();
}

function CountBars({ items }: { items: Item[] }) {
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
            <div
              className="h-2 rounded-full"
              style={{ width: `${(it.value / max) * 100}%`, background: it.color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const query = useQuery({ queryKey: ["overview"], queryFn: getOverview });
  const [fArea, setFArea] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fCrit, setFCrit] = useState("");
  const [fCat, setFCat] = useState("");
  const [fFrom, setFFrom] = useState("");
  const [fTo, setFTo] = useState("");

  const all = query.data?.projects ?? [];
  const areaOpts = useMemo(() => uniques(all, (p) => p.area_name), [all]);
  const critOpts = useMemo(() => uniques(all, (p) => p.criticality), [all]);
  const catOpts = useMemo(() => uniques(all, (p) => p.category), [all]);
  const statusOpts = useMemo(() => uniques(all, (p) => p.status), [all]);

  const filtered = useMemo(
    () =>
      all.filter(
        (p) =>
          (!fArea || p.area_name === fArea) &&
          (!fStatus || p.status === fStatus) &&
          (!fCrit || (p.criticality ?? "") === fCrit) &&
          (!fCat || (p.category ?? "") === fCat) &&
          (!fFrom || (p.due_date != null && p.due_date >= fFrom)) &&
          (!fTo || (p.due_date != null && p.due_date <= fTo)),
      ),
    [all, fArea, fStatus, fCrit, fCat, fFrom, fTo],
  );

  if (query.isLoading) return <Spinner label="Cargando analítica…" />;
  if (!query.data) return null;

  const hasFilter = fArea || fStatus || fCrit || fCat || fFrom || fTo;
  const clear = () => {
    setFArea("");
    setFStatus("");
    setFCrit("");
    setFCat("");
    setFFrom("");
    setFTo("");
  };

  const sum = (pick: (p: ProjectAnalytics) => number) => filtered.reduce((s, p) => s + pick(p), 0);
  const totalTasks = sum((p) => p.total);
  const doneTasks = sum((p) => p.done);
  const completion = totalTasks ? Math.round((doneTasks / totalTasks) * 100) : 0;
  const overdue = sum((p) => p.overdue);
  const atRisk = filtered.filter((p) => p.health === "en_riesgo").length;
  const active = filtered.filter((p) => p.status === "active").length;

  const statusSeg = segments(tally(filtered, (p) => p.status), PROJECT_STATUS_META);
  const critSeg = segments(
    tally(filtered, (p) => p.criticality || "Sin definir"),
    CRITICALITY_META,
  );
  const catItems = segments(topN(tally(filtered, (p) => p.category), 10));
  const initItems = segments(topN(tally(filtered, (p) => p.initiative), 10));
  const procItems = segments(topN(tally(filtered, (p) => p.process), 8));
  const taskStatusSeg = dictToItems(sumDict(filtered, "by_status"), STATUS_META);
  const priorityItems = dictToItems(sumDict(filtered, "by_priority"), PRIORITY_META);

  const buckets: Item[] = [
    ["0–25%", (p: ProjectAnalytics) => p.completion_pct <= 25],
    ["26–50%", (p: ProjectAnalytics) => p.completion_pct > 25 && p.completion_pct <= 50],
    ["51–75%", (p: ProjectAnalytics) => p.completion_pct > 50 && p.completion_pct <= 75],
    ["76–100%", (p: ProjectAnalytics) => p.completion_pct > 75],
  ].map(([label, test], i) => ({
    label: label as string,
    value: filtered.filter(test as (p: ProjectAnalytics) => boolean).length,
    color: BUCKET_COLORS[i],
  }));

  const byArea = areaOpts
    .map((area) => {
      const ps = filtered.filter((p) => p.area_name === area);
      const t = ps.reduce((s, p) => s + p.total, 0);
      const d = ps.reduce((s, p) => s + p.done, 0);
      return { area, projects: ps.length, pct: t ? Math.round((d / t) * 100) : 0 };
    })
    .filter((a) => a.projects > 0)
    .sort((a, b) => b.projects - a.projects);

  const ranking = filtered
    .filter((p) => p.total > 0)
    .slice()
    .sort((a, b) => b.completion_pct - a.completion_pct)
    .slice(0, 8);

  const attention = filtered
    .filter((p) => p.health === "en_riesgo" || p.health === "atencion" || p.overdue > 0)
    .slice(0, 10);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Inteligencia"
        title="Analítica"
        description="Avance y salud de la cartera de proyectos."
      />

      {/* Filtros */}
      <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card">
        <div className="w-40">
          <Select label="Área" value={fArea} onChange={(e) => setFArea(e.target.value)}>
            <option value="">Todas</option>
            {areaOpts.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </Select>
        </div>
        <div className="w-40">
          <Select label="Estado" value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
            <option value="">Todos</option>
            {statusOpts.map((s) => (
              <option key={s} value={s}>{PROJECT_STATUS_META[s]?.label ?? s}</option>
            ))}
          </Select>
        </div>
        <div className="w-40">
          <Select label="Criticidad" value={fCrit} onChange={(e) => setFCrit(e.target.value)}>
            <option value="">Todas</option>
            {critOpts.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </Select>
        </div>
        <div className="w-44">
          <Select label="Categoría" value={fCat} onChange={(e) => setFCat(e.target.value)}>
            <option value="">Todas</option>
            {catOpts.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Entrega</label>
          <div className="flex items-center gap-1.5">
            <input
              type="date"
              value={fFrom}
              onChange={(e) => setFFrom(e.target.value)}
              title="Entrega desde"
              className="h-10 rounded-xl border border-slate-300 bg-white px-2.5 text-sm text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
            <span className="text-slate-400">–</span>
            <input
              type="date"
              value={fTo}
              onChange={(e) => setFTo(e.target.value)}
              title="Entrega hasta"
              className="h-10 rounded-xl border border-slate-300 bg-white px-2.5 text-sm text-slate-600 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
        </div>
        {hasFilter && (
          <button
            type="button"
            onClick={clear}
            className="mb-0.5 inline-flex items-center gap-1 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-3.5 w-3.5" /> Limpiar
          </button>
        )}
        <span className="mb-1.5 ml-auto text-xs text-slate-400">
          {filtered.length} de {all.length} proyectos
        </span>
      </div>

      {/* KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Proyectos" value={filtered.length} hint={`${active} activos`} icon={<FolderKanban className="h-4 w-4" />} tone="brand" />
        <Kpi label="Avance global" value={`${completion}%`} hint={`${doneTasks}/${totalTasks} tareas`} icon={<TrendingUp className="h-4 w-4" />} tone="emerald" />
        <Kpi label="Tareas vencidas" value={overdue} hint={overdue ? "requieren acción" : "al día"} icon={<AlertTriangle className="h-4 w-4" />} tone={overdue ? "red" : "slate"} />
        <Kpi label="En riesgo" value={atRisk} hint={atRisk ? "vigilar de cerca" : "sin riesgos"} icon={<ShieldAlert className="h-4 w-4" />} tone={atRisk ? "red" : "slate"} />
      </div>

      {filtered.length === 0 ? (
        <Panel><p className="text-sm text-slate-500">Ningún proyecto coincide con los filtros.</p></Panel>
      ) : (
        <>
          {/* Distribuciones (donas) */}
          <div className="grid gap-5 lg:grid-cols-3">
            <Panel title="Proyectos por estado">
              <Donut segments={statusSeg} centerValue={`${filtered.length}`} centerLabel="proyectos" />
            </Panel>
            <Panel title="Criticidad">
              <Donut segments={critSeg} centerValue={`${filtered.length}`} centerLabel="proyectos" />
            </Panel>
            <Panel title="Tareas por estado">
              {totalTasks > 0 ? (
                <Donut segments={taskStatusSeg} centerValue={`${totalTasks}`} centerLabel="tareas" />
              ) : (
                <p className="text-sm text-slate-400">Sin tareas registradas.</p>
              )}
            </Panel>
          </div>

          {/* Categoría / iniciativa */}
          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Proyectos por categoría">
              <CountBars items={catItems} />
            </Panel>
            <Panel title="Proyectos por iniciativa">
              <CountBars items={initItems} />
            </Panel>
          </div>

          {/* Avance / prioridad / área */}
          <div className="grid gap-5 lg:grid-cols-3">
            <Panel title="Distribución de avance" subtitle="Proyectos por rango de % completado">
              <CountBars items={buckets} />
            </Panel>
            <Panel title="Tareas por prioridad">
              {priorityItems.length ? (
                <CountBars items={priorityItems} />
              ) : (
                <p className="text-sm text-slate-400">Sin tareas registradas.</p>
              )}
            </Panel>
            <Panel title="Avance por área">
              <div className="space-y-3.5">
                {byArea.map((a) => (
                  <div key={a.area}>
                    <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                      <span className="truncate font-medium text-slate-700">{a.area}</span>
                      <span className="shrink-0 text-slate-400">{a.projects} · {a.pct}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div className="h-2 rounded-full bg-brand-500" style={{ width: `${Math.max(a.pct, 1)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          {/* Ranking / proceso */}
          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Ranking de avance" subtitle="Proyectos con más progreso">
              {ranking.length === 0 ? (
                <p className="text-sm text-slate-400">Aún no hay tareas para medir avance.</p>
              ) : (
                <ul className="space-y-2.5">
                  {ranking.map((p) => (
                    <li key={p.project_id}>
                      <Link to={`/proyectos/${p.project_id}`} className="flex items-center gap-3 rounded-lg px-1 py-0.5 transition hover:bg-slate-50">
                        <span className="min-w-0 flex-1 truncate text-sm text-slate-700">{p.name}</span>
                        <div className="h-1.5 w-24 shrink-0 rounded-full bg-slate-100">
                          <div className="h-1.5 rounded-full bg-brand-500" style={{ width: `${Math.max(p.completion_pct, 1)}%` }} />
                        </div>
                        <span className="w-9 shrink-0 text-right text-xs tabular-nums text-slate-500">{p.completion_pct}%</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
            <Panel title="Proyectos por proceso">
              <CountBars items={procItems} />
            </Panel>
          </div>

          {/* Requiere atención */}
          <Panel title="Requiere atención" subtitle="Proyectos en riesgo, en alerta o con tareas vencidas">
            {attention.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-emerald-600">
                <CheckCircle2 className="h-4 w-4" /> Todo en orden, sin proyectos en riesgo.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                      <th className="pb-2 pr-3">Proyecto</th>
                      <th className="pb-2 pr-3">Salud</th>
                      <th className="pb-2 pr-3 text-right">Vencidas</th>
                      <th className="pb-2 pr-3 text-right">Bloqueadas</th>
                      <th className="pb-2 text-right">Entrega</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {attention.map((p) => {
                      const h = HEALTH[p.health] ?? { label: p.health, tone: "neutral" as const };
                      return (
                        <tr key={p.project_id} className="transition hover:bg-slate-50">
                          <td className="py-2 pr-3">
                            <Link to={`/proyectos/${p.project_id}`} className="font-medium text-slate-800 hover:text-brand-600">
                              {p.name}
                            </Link>
                          </td>
                          <td className="py-2 pr-3"><Badge tone={h.tone} dot>{h.label}</Badge></td>
                          <td className="py-2 pr-3 text-right tabular-nums text-slate-600">{p.overdue || "—"}</td>
                          <td className="py-2 pr-3 text-right tabular-nums text-slate-600">{p.blocked || "—"}</td>
                          <td className="py-2 text-right text-xs text-slate-500">
                            {p.due_in_days == null ? "—" : p.due_in_days < 0 ? `${-p.due_in_days}d tarde` : `en ${p.due_in_days}d`}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
