import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getQuarterlyTracking } from "../api/analytics";
import { PercentBars } from "./charts";
import { Card, Kpi, Panel, Spinner } from "./ui";

const QUARTERS = [
  { q: 1, label: "T1", months: "Ene–Mar" },
  { q: 2, label: "T2", months: "Abr–Jun" },
  { q: 3, label: "T3", months: "Jul–Sep" },
  { q: 4, label: "T4", months: "Oct–Dic" },
];

export function QuarterlyTracking() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [quarter, setQuarter] = useState(Math.floor(now.getMonth() / 3) + 1);

  const q = useQuery({
    queryKey: ["quarterly", year, quarter],
    queryFn: () => getQuarterlyTracking(year, quarter),
    placeholderData: (prev) => prev,
  });
  const d = q.data;

  // Años disponibles según los datos, incluyendo siempre el año actual.
  const lo = Math.min(d?.min_year ?? now.getFullYear(), now.getFullYear());
  const hi = Math.max(d?.max_year ?? now.getFullYear(), now.getFullYear());
  const years: number[] = [];
  for (let y = hi; y >= lo; y--) years.push(y);

  const chartItems = (d?.by_category ?? []).map((c) => ({
    label: c.category,
    value: c.avg_progress,
  }));

  return (
    <div className="space-y-5">
      {/* Selector de trimestre */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="h-9 rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        >
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <div className="inline-flex overflow-hidden rounded-xl border border-slate-300">
          {QUARTERS.map((qq, i) => (
            <button
              key={qq.q}
              type="button"
              onClick={() => setQuarter(qq.q)}
              title={qq.months}
              className={`px-3.5 py-1.5 text-sm font-medium transition ${
                i > 0 ? "border-l border-slate-300" : ""
              } ${quarter === qq.q ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
            >
              {qq.label}
            </button>
          ))}
        </div>
        {d && (
          <span className="ml-auto text-xs text-slate-400">
            {d.is_current
              ? "Trimestre en curso · avance actual"
              : "Cerrado · avance al finalizar el trimestre"}
          </span>
        )}
      </div>

      {q.isLoading && !d ? (
        <Spinner label="Cargando trimestre…" />
      ) : !d ? null : (
        <>
          <h2 className="text-center text-lg font-bold uppercase tracking-wide text-slate-700">
            {d.label}
          </h2>

          {/* KPIs + gráfico, como el tablero */}
          <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
              <Kpi label="Total de proyectos trabajados" value={d.total_projects} tone="brand" />
              <Kpi
                label="% de avance al finalizar el trimestre"
                value={`${d.avg_progress}%`}
                hint={d.is_current ? "avance actual" : "al cierre"}
                tone="emerald"
              />
            </div>
            <Panel title="% de avance por categoría">
              {chartItems.length === 0 ? (
                <p className="py-12 text-center text-sm text-slate-400">
                  Sin proyectos con fechas que crucen este trimestre.
                </p>
              ) : (
                <PercentBars items={chartItems} />
              )}
            </Panel>
          </div>

          {/* Tabla por categoría / proceso */}
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-2.5">Categoría / Proceso</th>
                    <th className="px-4 py-2.5 text-right">Cantidad proyectos trabajados</th>
                    <th className="px-4 py-2.5 text-right">% avance para el trimestre</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {d.by_category.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-4 py-6 text-center text-sm text-slate-400">
                        Sin datos para el trimestre.
                      </td>
                    </tr>
                  ) : (
                    d.by_category.map((c) => (
                      <tr key={c.category} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 font-medium text-slate-700">{c.category}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-slate-600">{c.count}</td>
                        <td className="px-4 py-2.5 text-right font-semibold tabular-nums text-slate-800">
                          {c.avg_progress}%
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
                <tfoot>
                  <tr className="border-t border-slate-200 bg-slate-50 font-semibold text-slate-800">
                    <td className="px-4 py-2.5">Suma total</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{d.total_projects}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{d.avg_progress}%</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>

          {d.without_dates > 0 && (
            <p className="text-xs text-slate-400">
              {d.without_dates} proyecto{d.without_dates === 1 ? "" : "s"} sin fechas no aparece
              {d.without_dates === 1 ? "" : "n"} aquí. Asigna inicio y entrega en cada proyecto para
              incluirlos en el seguimiento trimestral.
            </p>
          )}
        </>
      )}
    </div>
  );
}
