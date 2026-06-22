import { useMutation, useQuery } from "@tanstack/react-query";
import mermaid from "mermaid";
import { Check, FolderPlus, Workflow } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { createDocument } from "../api/knowledge";
import { listProjects } from "../api/projects";

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

/** Botón + selector para guardar el diagrama en la documentación de un proyecto. */
function SaveToProject({ code }: { code: string }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("Diagrama");
  const [projectId, setProjectId] = useState<number | "">("");
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects, enabled: open });

  const save = useMutation({
    mutationFn: () => createDocument(Number(projectId), title.trim() || "Diagrama", code, "diagram"),
    onSuccess: () => setOpen(false),
  });

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium text-slate-500 transition hover:bg-slate-100 hover:text-brand-700"
      >
        <FolderPlus className="h-3.5 w-3.5" /> Guardar en proyecto
      </button>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Título"
        className="h-7 w-28 rounded-md border border-slate-300 px-2 text-xs focus:border-brand-500 focus:outline-none"
      />
      <select
        value={projectId}
        onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : "")}
        className="h-7 max-w-[160px] rounded-md border border-slate-300 px-1.5 text-xs focus:border-brand-500 focus:outline-none"
      >
        <option value="">Proyecto…</option>
        {(projects.data ?? []).map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <button
        type="button"
        disabled={!projectId || save.isPending}
        onClick={() => save.mutate()}
        className="inline-flex items-center gap-1 rounded-md bg-brand-600 px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-brand-700 disabled:opacity-40"
      >
        <Check className="h-3 w-3" /> {save.isPending ? "…" : "Guardar"}
      </button>
      <button type="button" onClick={() => setOpen(false)} className="text-[11px] text-slate-400 hover:text-slate-600">
        Cancelar
      </button>
    </div>
  );
}

/** Renderiza un bloque ```mermaid``` como diagrama (flujo, secuencia, etc.). */
export default function Mermaid({ code, saveable = false }: { code: string; saveable?: boolean }) {
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
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-1.5">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          <Workflow className="h-3.5 w-3.5 text-brand-500" /> Diagrama
        </span>
        {saveable && <SaveToProject code={code} />}
      </div>
      <div ref={ref} className="overflow-x-auto p-4 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full" />
    </div>
  );
}
