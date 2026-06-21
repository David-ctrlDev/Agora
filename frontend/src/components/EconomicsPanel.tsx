import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

import { type EconomicsUpdate, getEconomics, updateEconomics } from "../api/economics";
import { Button, Card, Input, Select, Spinner } from "./ui";

const CURRENCIES = ["COP", "USD", "EUR", "MXN"];

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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-medium tabular-nums text-slate-800">{value}</div>
    </div>
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

export default function EconomicsPanel({
  projectId,
  canEdit,
}: {
  projectId: number;
  canEdit: boolean;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["economics", projectId],
    queryFn: () => getEconomics(projectId),
  });
  const data = query.data;

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    estimated_cost: "",
    actual_cost: "",
    expected_benefit: "",
    actual_benefit: "",
    currency: "COP",
  });

  useEffect(() => {
    if (data) {
      setForm({
        estimated_cost: data.estimated_cost?.toString() ?? "",
        actual_cost: data.actual_cost?.toString() ?? "",
        expected_benefit: data.expected_benefit?.toString() ?? "",
        actual_benefit: data.actual_benefit?.toString() ?? "",
        currency: data.currency,
      });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () => {
      const num = (s: string) => (s.trim() === "" ? null : Number(s));
      const payload: EconomicsUpdate = {
        estimated_cost: num(form.estimated_cost),
        actual_cost: num(form.actual_cost),
        expected_benefit: num(form.expected_benefit),
        actual_benefit: num(form.actual_benefit),
        currency: form.currency,
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

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <TrendingUp className="h-4 w-4 text-slate-400" /> ROI y beneficios
        </h2>
        {canEdit && !editing && (
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
            <Pencil className="h-4 w-4" /> {data.has_data ? "Editar" : "Registrar cifras"}
          </Button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Costo estimado"
              type="number"
              min="0"
              value={form.estimated_cost}
              onChange={(ev) => setForm({ ...form, estimated_cost: ev.target.value })}
            />
            <Input
              label="Costo real"
              type="number"
              min="0"
              value={form.actual_cost}
              onChange={(ev) => setForm({ ...form, actual_cost: ev.target.value })}
            />
            <Input
              label="Beneficio esperado"
              type="number"
              min="0"
              value={form.expected_benefit}
              onChange={(ev) => setForm({ ...form, expected_benefit: ev.target.value })}
            />
            <Input
              label="Beneficio realizado"
              type="number"
              min="0"
              value={form.actual_benefit}
              onChange={(ev) => setForm({ ...form, actual_benefit: ev.target.value })}
            />
          </div>
          <div className="w-40">
            <Select
              label="Moneda"
              value={form.currency}
              onChange={(ev) => setForm({ ...form, currency: ev.target.value })}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Cancelar
            </Button>
            <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
              Guardar
            </Button>
          </div>
        </div>
      ) : !data.has_data ? (
        <p className="text-sm text-slate-500">
          Aún no hay cifras económicas.{canEdit && " Regístralas para calcular el ROI."}
        </p>
      ) : (
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Retorno (ROI) {roiKind}
              </div>
              <div
                className={`mt-1 text-3xl font-semibold ${roi != null && roi < 0 ? "text-red-600" : "text-emerald-600"}`}
              >
                {roi == null ? "—" : `${roi}%`}
              </div>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Beneficio neto {netKind}
              </div>
              <div
                className={`mt-1 text-3xl font-semibold ${net != null && net < 0 ? "text-red-600" : "text-slate-900"}`}
              >
                {formatMoney(net, data.currency)}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Costo estimado" value={formatMoney(data.estimated_cost, data.currency)} />
            <Metric label="Costo real" value={formatMoney(data.actual_cost, data.currency)} />
            <Metric
              label="Beneficio esperado"
              value={formatMoney(data.expected_benefit, data.currency)}
            />
            <Metric
              label="Beneficio realizado"
              value={formatMoney(data.actual_benefit, data.currency)}
            />
          </div>

          <div className="space-y-3">
            <Bar label="Presupuesto consumido" pct={data.cost_consumption_pct} color="#f59e0b" />
            <Bar label="Beneficio realizado" pct={data.benefit_realization_pct} color="#10b981" />
          </div>
        </div>
      )}
    </Card>
  );
}
