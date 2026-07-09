import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Coins, Cpu, MessageSquare, Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import { type CostRow, deletePricing, getCostSummary, getPricing, upsertPricing } from "../api/costs";
import { useMe } from "../auth/useAuth";
import { Button, Card, Input, Kpi, PageHeader, Panel, Spinner } from "../components/ui";

const usd = (n: number) =>
  `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
const nfmt = (n: number) => n.toLocaleString("es-CO");

function DayBars({ items }: { items: { day: string; cost_usd: number }[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">Sin consumo todavía.</p>;
  const max = Math.max(...items.map((i) => i.cost_usd), 0.000001);
  return (
    <div className="space-y-2">
      {items.map((it) => (
        <div key={it.day} className="flex items-center gap-3">
          <span className="w-16 shrink-0 text-xs tabular-nums text-slate-400">{it.day.slice(5)}</span>
          <div className="h-2.5 flex-1 rounded-full bg-slate-100">
            <div
              className="h-2.5 rounded-full bg-brand-500"
              style={{ width: `${Math.max((it.cost_usd / max) * 100, 2)}%` }}
            />
          </div>
          <span className="w-20 shrink-0 text-right text-xs tabular-nums text-slate-600">
            {usd(it.cost_usd)}
          </span>
        </div>
      ))}
    </div>
  );
}

function RowsTable({ title, rows }: { title: string; rows: CostRow[] }) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="border-b border-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-700">
        {title}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2 text-right">Llamadas</th>
              <th className="px-4 py-2 text-right">Tokens</th>
              <th className="px-4 py-2 text-right">Costo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-4 text-center text-sm text-slate-400">
                  Sin datos.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.key} className="hover:bg-slate-50">
                  <td className="px-4 py-2 text-slate-700">{r.key}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500">{r.calls}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500">{nfmt(r.tokens)}</td>
                  <td className="px-4 py-2 text-right font-medium tabular-nums text-slate-800">
                    {usd(r.cost_usd)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/** Tarifas por modelo — solo el super admin puede crear/editar/eliminar. */
function PricingPanel() {
  const qc = useQueryClient();
  const pricing = useQuery({ queryKey: ["costs-pricing"], queryFn: getPricing });
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["costs-pricing"] });
    qc.invalidateQueries({ queryKey: ["costs"] });
  };

  const [model, setModel] = useState("");
  const [inp, setInp] = useState("");
  const [outp, setOutp] = useState("");

  const save = useMutation({
    mutationFn: () =>
      upsertPricing({
        model: model.trim(),
        input_per_1m: Number(inp),
        output_per_1m: Number(outp),
      }),
    onSuccess: () => {
      invalidate();
      setModel("");
      setInp("");
      setOutp("");
    },
  });
  const del = useMutation({ mutationFn: (id: number) => deletePricing(id), onSuccess: invalidate });

  const valid = model.trim() && inp !== "" && outp !== "" && Number(inp) >= 0 && Number(outp) >= 0;
  const rows = pricing.data ?? [];

  return (
    <Panel
      title="Tarifas por modelo"
      subtitle="USD por 1M de tokens. Los cambios aplican a consumos futuros."
    >
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (valid) save.mutate();
        }}
        className="mb-4 flex flex-wrap items-end gap-3"
      >
        <div className="min-w-[220px] flex-1">
          <Input
            label="Modelo"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="p. ej. gemini-flash-latest"
          />
        </div>
        <div className="w-44">
          <Input
            label="Entrada (USD / 1M)"
            type="number"
            step="0.001"
            min="0"
            value={inp}
            onChange={(e) => setInp(e.target.value)}
            placeholder="0.10"
          />
        </div>
        <div className="w-44">
          <Input
            label="Salida (USD / 1M)"
            type="number"
            step="0.001"
            min="0"
            value={outp}
            onChange={(e) => setOutp(e.target.value)}
            placeholder="0.40"
          />
        </div>
        <Button type="submit" disabled={!valid || save.isPending}>
          <Plus className="h-4 w-4" /> {save.isPending ? "Guardando…" : "Guardar tarifa"}
        </Button>
      </form>
      {save.isError && (
        <p className="mb-3 text-sm text-rose-600">No se pudo guardar la tarifa.</p>
      )}

      {pricing.isLoading ? (
        <Spinner label="Cargando tarifas…" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-slate-400">
          Sin tarifas: el consumo se registrará con costo $0 hasta definirlas.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-2 py-2">Modelo</th>
                <th className="px-2 py-2 text-right">Entrada / 1M</th>
                <th className="px-2 py-2 text-right">Salida / 1M</th>
                <th className="px-2 py-2 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-2 py-2 font-medium text-slate-800">{p.model}</td>
                  <td className="px-2 py-2 text-right tabular-nums text-slate-600">{usd(p.input_per_1m)}</td>
                  <td className="px-2 py-2 text-right tabular-nums text-slate-600">{usd(p.output_per_1m)}</td>
                  <td className="px-2 py-2 text-right">
                    <div className="inline-flex gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          setModel(p.model);
                          setInp(String(p.input_per_1m));
                          setOutp(String(p.output_per_1m));
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                      >
                        <Pencil className="h-3.5 w-3.5" /> Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(`¿Eliminar la tarifa de «${p.model}»?`)) del.mutate(p.id);
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Eliminar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function CostsPage() {
  const me = useMe();
  const q = useQuery({ queryKey: ["costs"], queryFn: getCostSummary });

  const allowed = me.data?.is_superadmin || me.data?.can_view_costs;
  if (me.data && !allowed) {
    return (
      <Panel>
        <p className="text-sm text-slate-500">No tienes acceso al módulo de costos.</p>
      </Panel>
    );
  }
  if (q.isLoading) return <Spinner label="Cargando costos…" />;
  const d = q.data;
  if (!d) return null;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Costos"
        title="Costo del agente IA"
        description="Consumo de tokens del asistente y su costo estimado."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Costo del mes" value={usd(d.month_cost_usd)} hint="estimado (USD)" icon={<Coins className="h-4 w-4" />} tone="brand" />
        <Kpi label="Costo total" value={usd(d.total_cost_usd)} hint="histórico" icon={<CalendarClock className="h-4 w-4" />} tone="emerald" />
        <Kpi label="Tokens totales" value={nfmt(d.total_tokens)} hint={`${nfmt(d.total_calls)} llamadas`} icon={<Cpu className="h-4 w-4" />} tone="slate" />
        <Kpi label="Llamadas al modelo" value={nfmt(d.total_calls)} hint="al agente" icon={<MessageSquare className="h-4 w-4" />} tone="slate" />
      </div>

      <Panel title="Costo por día" subtitle="Últimos 30 días">
        <DayBars items={d.by_day} />
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        <RowsTable title="Por usuario" rows={d.by_user} />
        <RowsTable title="Por modelo" rows={d.by_model} />
      </div>

      {me.data?.is_superadmin && <PricingPanel />}

      <p className="text-xs text-slate-400">
        Costo estimado según las tarifas por modelo. El importe real de Google puede variar.
      </p>
    </div>
  );
}
