import mermaid from "mermaid";
import { Workflow } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

let initialized = false;

/** Inicializa Mermaid una sola vez, con un tema acorde a la marca (esmeralda + slate). */
function ensureInit() {
  if (initialized) return;
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "base",
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
    themeVariables: {
      primaryColor: "#ecfdf5",
      primaryBorderColor: "#059669",
      primaryTextColor: "#0f172a",
      secondaryColor: "#f1f5f9",
      secondaryBorderColor: "#cbd5e1",
      tertiaryColor: "#f8fafc",
      lineColor: "#94a3b8",
      fontSize: "14px",
    },
  });
  initialized = true;
}

/** Renderiza un bloque ```mermaid``` como diagrama (flujo, secuencia, etc.). */
export default function Mermaid({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    ensureInit();
    mermaid
      .render(`mmd-${id}`, code)
      .then(({ svg }) => {
        if (cancelled) return;
        setError(false);
        if (ref.current) ref.current.innerHTML = svg;
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [code, id]);

  // Si la sintaxis no es válida, mostramos el código en bruto en vez de romper el chat.
  if (error) {
    return (
      <pre className="my-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
        <code>{code}</code>
      </pre>
    );
  }

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-soft">
      <div className="flex items-center gap-1.5 border-b border-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        <Workflow className="h-3.5 w-3.5 text-brand-500" /> Diagrama
      </div>
      <div
        ref={ref}
        className="overflow-x-auto p-4 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      />
    </div>
  );
}
