import { type ReactNode } from "react";

interface PanelProps {
  title?: ReactNode;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

/** Tarjeta-panel con cabecera, estilo reporte BI. */
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
  bodyClassName = "p-5",
}: PanelProps) {
  return (
    <div
      className={`flex flex-col rounded-2xl border border-slate-200/80 bg-white shadow-card ${className}`}
    >
      {(title || actions) && (
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
          <div className="min-w-0">
            {title && <h3 className="truncate text-sm font-semibold text-slate-800">{title}</h3>}
            {subtitle && <p className="truncate text-xs text-slate-400">{subtitle}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      <div className={`flex-1 ${bodyClassName}`}>{children}</div>
    </div>
  );
}
