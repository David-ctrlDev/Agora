import { type ReactNode } from "react";

type KpiTone = "brand" | "emerald" | "amber" | "red" | "slate";

const toneChip: Record<KpiTone, string> = {
  brand: "bg-brand-50 text-brand-600",
  emerald: "bg-emerald-50 text-emerald-600",
  amber: "bg-amber-50 text-amber-600",
  red: "bg-red-50 text-red-600",
  slate: "bg-slate-100 text-slate-500",
};

interface KpiProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: KpiTone;
}

/** Métrica grande para tiras de KPIs (dashboard). */
export function Kpi({ label, value, hint, icon, tone = "slate" }: KpiProps) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card transition hover:shadow-pop">
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</span>
        {icon && (
          <span
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${toneChip[tone]}`}
          >
            {icon}
          </span>
        )}
      </div>
      <div className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}
