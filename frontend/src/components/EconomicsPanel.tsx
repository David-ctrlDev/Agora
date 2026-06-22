import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Cog, Pencil, ShieldCheck, Sparkles, TrendingUp, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { listAreas } from "../api/areas";
import { type EconomicsUpdate, type Level, getEconomics, updateEconomics } from "../api/economics";
import { Button, Card, Input, Select, Spinner, Textarea } from "./ui";

const CURRENCIES = ["COP", "USD", "EUR", "MXN"];
const LEVELS: { value: Level; label: string }[] = [
  { value: "low", label: "Baja" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
];
const LEVEL_LABEL: Record<string, string> = { low: "Baja", medium: "Media", high: "Alta" };

function formatMoney(value: number | null, currency: string) {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${value.toLocaleString("es-CO")} ${currency}`;
  }
}

const num = (v: number | null, suffix = "") => (v == null ? "—" : `${v.toLocaleString("es-CO")}${suffix}`);

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null || value === "—" || value === "") return null;
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium tabular-nums text-slate-800">{value}</span>
    </div>
  );
}

function LevelChip({ value }: { value: Level | null }) {
  if (!value) return <>—</>;
  return (
    <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-semibold text-slate-600">
      {LEVEL_LABEL[value]}
    </span>
  );
}

function Bar({ label, pct, color }: { label: string; pct: number | null; color: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-500">
        <span>{label}</span>
        <span className="tabular-nums">{pct == null ? "—" : `${pct}%`}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div
          className="h-2 rounded-full"
          style={{ width: `${Math.min(100, pct ?? 0)}%`, background: color }}
        />
      </div>
    </div>
  );
}

function Highlight({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-slate-200/70 bg-white px-3 py-2">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
        {icon}
      </span>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-slate-800">{value}</div>
        <div className="truncate text-[11px] text-slate-400">{label}</div>
      </div>
    </div>
  );
}

const EMPTY = {
  estimated_cost: "",
  actual_cost: "",
  expected_benefit: "",
  actual_benefit: "",
  currency: "COP",
  effort_hours_estimated: "",
  effort_hours_actual: "",
  executor_team: "",
  implementation_complexity: "",
  resources_needed: "",
  beneficiary_area_id: "",
  beneficiary_process: "",
  hours_saved_monthly: "",
  people_impacted: "",
  risk_reduction: "",
  strategic_value: "",
};

export default function EconomicsPanel({ projectId, canEdit }: { projectId: number; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["economics", projectId], queryFn: () => getEconomics(projectId) });
  const areasQuery = useQuery({ queryKey: ["areas"], queryFn: listAreas });
  const data = query.data;

  const areaName = useMemo(() => {
    const map = new Map<number, string>();
    (areasQuery.data ?? []).forEach((a) => map.set(a.id, a.name));
    return map;
  }, [areasQuery.data]);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ ...EMPTY });
  const set = (k: keyof typeof EMPTY, v: string) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    if (!data) return;
    const s = (v: number | null) => (v == null ? "" : String(v));
    setForm({
      estimated_cost: s(data.estimated_cost),
      actual_cost: s(data.actual_cost),
      expected_benefit: s(data.expected_benefit),
      actual_benefit: s(data.actual_benefit),
      currency: data.currency,
      effort_hours_estimated: s(data.effort_hours_estimated),
      effort_hours_actual: s(data.effort_hours_actual),
      executor_team: data.executor_team ?? "",
      implementation_complexity: data.implementation_complexity ?? "",
      resources_needed: data.resources_needed ?? "",
      beneficiary_area_id: data.beneficiary_area_id == null ? "" : String(data.beneficiary_area_id),
      beneficiary_process: data.beneficiary_process ?? "",
      hours_saved_monthly: s(data.hours_saved_monthly),
      people_impacted: s(data.people_impacted),
      risk_reduction: data.risk_reduction ?? "",
      strategic_value: data.strategic_value ?? "",
    });
  }, [data]);

  const save = useMutation({
    mutationFn: () => {
      const n = (x: string) => (x.trim() === "" ? null : Number(x));
      const lvl = (x: string) => (x ? (x as Level) : null);
      const t = (x: string) => (x.trim() === "" ? null : x.trim());
      const payload: EconomicsUpdate = {
        estimated_cost: n(form.estimated_cost),
        actual_cost: n(form.actual_cost),
        expected_benefit: n(form.expected_benefit),
        actual_benefit: n(form.actual_benefit),
        currency: form.currency,
        effort_hours_estimated: n(form.effort_hours_estimated),
        effort_hours_actual: n(form.effort_hours_actual),
        executor_team: t(form.executor_team),
        implementation_complexity: lvl(form.implementation_complexity),
        resources_needed: t(form.resources_needed),
        beneficiary_area_id: form.beneficiary_area_id ? Number(form.beneficiary_area_id) : null,
        beneficiary_process: t(form.beneficiary_process),
        hours_saved_monthly: n(form.hours_saved_monthly),
        people_impacted: n(form.people_impacted),
        risk_reduction: lvl(form.risk_reduction),
        strategic_value: lvl(form.strategic_value),
      };
      return updateEconomics(projectId, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["economics", projectId] });
      setEditing(false);
    },
  });

  if (query.isLoading) {
    return (
      <Card className="p-5">
        <Spinner label="Cargando ROI…" />
      </Card>
    );
  }
  if (!data) return null;

  const roi = data.roi_actual_pct ?? data.roi_expected_pct;
  const roiKind = data.roi_actual_pct != null ? "real" : "esperado";
  const net = data.net_actual ?? data.net_expected;
  const netKind = data.net_actual != null ? "real" : "esperado";
  const cur = data.currency;
  const anything = data.has_data || data.has_impact;

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <TrendingUp className="h-4 w-4 text-slate-400" /> ROI, impacto y beneficios
        </h2>
        {canEdit && !editing && (
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
            <Pencil className="h-4 w-4" /> {anything ? "Editar" : "Registrar"}
          </Button>
        )}
      </div>

      {editing ? (
        <div className="space-y-5">
          {/* Lado ejecutor */}
          <div className="rounded-xl border border-slate-200 p-4">
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Cog className="h-4 w-4 text-slate-400" /> Proceso que lo hace (inversión)
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input label="Costo estimado" type="number" min="0" value={form.estimated_cost} onChange={(e) => set("estimated_cost", e.target.value)} />
              <Input label="Costo real" type="number" min="0" value={form.actual_cost} onChange={(e) => set("actual_cost", e.target.value)} />
              <Input label="Esfuerzo estimado (horas)" type="number" min="0" value={form.effort_hours_estimated} onChange={(e) => set("effort_hours_estimated", e.target.value)} />
              <Input label="Esfuerzo real (horas)" type="number" min="0" value={form.effort_hours_actual} onChange={(e) => set("effort_hours_actual", e.target.value)} />
              <Input label="Equipo / roles dedicados" value={form.executor_team} onChange={(e) => set("executor_team", e.target.value)} placeholder="2 analistas BI, 1 PM…" />
              <Select label="Complejidad / riesgo" value={form.implementation_complexity} onChange={(e) => set("implementation_complexity", e.target.value)}>
                <option value="">—</option>
                {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </Select>
            </div>
            <div className="mt-3">
              <Textarea label="Recursos / herramientas" rows={2} value={form.resources_needed} onChange={(e) => set("resources_needed", e.target.value)} placeholder="Licencias, infraestructura, datos…" />
            </div>
          </div>

          {/* Lado beneficiario */}
          <div className="rounded-xl border border-slate-200 p-4">
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Sparkles className="h-4 w-4 text-brand-500" /> Proceso para el que se hace (retorno)
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <Select label="Área beneficiaria" value={form.beneficiary_area_id} onChange={(e) => set("beneficiary_area_id", e.target.value)}>
                <option value="">—</option>
                {(areasQuery.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </Select>
              <Input label="Proceso beneficiario" value={form.beneficiary_process} onChange={(e) => set("beneficiary_process", e.target.value)} placeholder="Nómina, despachos…" />
              <Input label="Beneficio esperado" type="number" min="0" value={form.expected_benefit} onChange={(e) => set("expected_benefit", e.target.value)} />
              <Input label="Beneficio realizado" type="number" min="0" value={form.actual_benefit} onChange={(e) => set("actual_benefit", e.target.value)} />
              <Input label="Horas ahorradas / mes" type="number" min="0" value={form.hours_saved_monthly} onChange={(e) => set("hours_saved_monthly", e.target.value)} />
              <Input label="Personas impactadas" type="number" min="0" value={form.people_impacted} onChange={(e) => set("people_impacted", e.target.value)} />
              <Select label="Reducción de errores / riesgo" value={form.risk_reduction} onChange={(e) => set("risk_reduction", e.target.value)}>
                <option value="">—</option>
                {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </Select>
              <Select label="Valor estratégico" value={form.strategic_value} onChange={(e) => set("strategic_value", e.target.value)}>
                <option value="">—</option>
                {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="w-32">
              <Select label="Moneda" value={form.currency} onChange={(e) => set("currency", e.target.value)}>
                {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </Select>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancelar</Button>
              <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>Guardar</Button>
            </div>
          </div>
        </div>
      ) : !anything ? (
        <p className="text-sm text-slate-500">
          Aún no hay cifras ni impacto registrados.{canEdit && " Regístralos para calcular el ROI y el retorno."}
        </p>
      ) : (
        <div className="space-y-5">
          {/* Resumen monetario */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-400">Retorno (ROI) {roiKind}</div>
              <div className={`mt-1 text-3xl font-semibold ${roi != null && roi < 0 ? "text-red-600" : "text-emerald-600"}`}>
                {roi == null ? "—" : `${roi}%`}
              </div>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-400">Beneficio neto {netKind}</div>
              <div className={`mt-1 text-3xl font-semibold ${net != null && net < 0 ? "text-red-600" : "text-slate-900"}`}>
                {formatMoney(net, cur)}
              </div>
            </div>
          </div>

          {/* Impacto no monetario destacado */}
          {data.has_impact && (
            <div className="grid gap-2 sm:grid-cols-3">
              {data.hours_saved_yearly != null && (
                <Highlight icon={<Clock className="h-4 w-4" />} label="Horas ahorradas / año" value={num(data.hours_saved_yearly, " h")} />
              )}
              {data.people_impacted != null && (
                <Highlight icon={<Users className="h-4 w-4" />} label="Personas impactadas" value={num(data.people_impacted)} />
              )}
              {data.strategic_value && (
                <Highlight icon={<ShieldCheck className="h-4 w-4" />} label="Valor estratégico" value={LEVEL_LABEL[data.strategic_value]} />
              )}
            </div>
          )}

          {/* Dos procesos */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200/70 p-4">
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Cog className="h-4 w-4 text-slate-400" /> Proceso que lo hace
              </h3>
              <Row label="Área" value={data.executor_area_id != null ? areaName.get(data.executor_area_id) ?? "—" : "—"} />
              <Row label="Proceso" value={data.executor_process} />
              <Row label="Costo estimado" value={formatMoney(data.estimated_cost, cur)} />
              <Row label="Costo real" value={formatMoney(data.actual_cost, cur)} />
              <Row label="Esfuerzo estimado" value={num(data.effort_hours_estimated, " h")} />
              <Row label="Esfuerzo real" value={data.effort_hours_actual == null ? null : `${num(data.effort_hours_actual, " h")}${data.effort_variance_pct != null ? ` (${data.effort_variance_pct > 0 ? "+" : ""}${data.effort_variance_pct}%)` : ""}`} />
              <Row label="Equipo / roles" value={data.executor_team} />
              <Row label="Complejidad / riesgo" value={data.implementation_complexity ? <LevelChip value={data.implementation_complexity} /> : null} />
              <Row label="Recursos" value={data.resources_needed} />
            </div>

            <div className="rounded-xl border border-slate-200/70 p-4">
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Sparkles className="h-4 w-4 text-brand-500" /> Proceso para el que se hace
              </h3>
              <Row label="Área" value={data.beneficiary_area_id != null ? areaName.get(data.beneficiary_area_id) ?? "—" : "—"} />
              <Row label="Proceso" value={data.beneficiary_process} />
              <Row label="Beneficio esperado" value={formatMoney(data.expected_benefit, cur)} />
              <Row label="Beneficio realizado" value={formatMoney(data.actual_benefit, cur)} />
              <Row label="Horas ahorradas / mes" value={num(data.hours_saved_monthly, " h")} />
              <Row label="Horas ahorradas / año" value={num(data.hours_saved_yearly, " h")} />
              <Row label="Personas impactadas" value={num(data.people_impacted)} />
              <Row label="Reducción de errores / riesgo" value={data.risk_reduction ? <LevelChip value={data.risk_reduction} /> : null} />
              <Row label="Valor estratégico" value={data.strategic_value ? <LevelChip value={data.strategic_value} /> : null} />
            </div>
          </div>

          {data.has_data && (
            <div className="space-y-3">
              <Bar label="Presupuesto consumido" pct={data.cost_consumption_pct} color="#f59e0b" />
              <Bar label="Beneficio realizado" pct={data.benefit_realization_pct} color="#10b981" />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
