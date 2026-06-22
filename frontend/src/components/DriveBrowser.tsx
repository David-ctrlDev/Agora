import { useQuery } from "@tanstack/react-query";
import {
  ChevronRight,
  File as FileIcon,
  FileSpreadsheet,
  FileText,
  Folder,
  Image as ImageIcon,
  Presentation,
  Search,
  X,
} from "lucide-react";
import { type CSSProperties, type RefObject, useEffect, useLayoutEffect, useMemo, useState } from "react";

import { type DriveEntry, browseDrive } from "../api/google";
import { Spinner } from "./ui";

interface Crumb {
  id: string | null;
  name: string;
}

interface Props {
  title?: string;
  actionLabel: string;
  multiSelect?: boolean;
  busy?: boolean;
  pendingId?: string | null;
  anchorRef?: RefObject<HTMLElement | null>;
  onClose: () => void;
  onPick?: (entry: DriveEntry) => void;
  onConfirm?: (entries: DriveEntry[]) => void;
}

const CENTERED: CSSProperties = {
  left: "50%",
  top: "50%",
  transform: "translate(-50%, -50%)",
  width: "min(440px, calc(100vw - 1rem))",
  maxHeight: "80vh",
};

function fileIcon(mime: string | null) {
  const m = mime ?? "";
  if (m.includes("spreadsheet") || m.includes("excel") || m.endsWith("csv"))
    return <FileSpreadsheet className="h-4 w-4 text-emerald-600" />;
  if (m.includes("presentation") || m.includes("powerpoint"))
    return <Presentation className="h-4 w-4 text-amber-600" />;
  if (m.startsWith("image/")) return <ImageIcon className="h-4 w-4 text-purple-500" />;
  if (m.includes("document") || m.includes("word") || m === "application/pdf" || m.startsWith("text/"))
    return <FileText className="h-4 w-4 text-brand-600" />;
  return <FileIcon className="h-4 w-4 text-slate-400" />;
}

export default function DriveBrowser({
  title = "Tu Google Drive",
  actionLabel,
  multiSelect = false,
  busy = false,
  pendingId = null,
  anchorRef,
  onClose,
  onPick,
  onConfirm,
}: Props) {
  const [scope, setScope] = useState<"mine" | "shared">("mine");
  const [stack, setStack] = useState<Crumb[]>([{ id: null, name: "Mi unidad" }]);
  const [term, setTerm] = useState("");
  const [debounced, setDebounced] = useState("");
  const [selected, setSelected] = useState<Record<string, DriveEntry>>({});
  const [panelStyle, setPanelStyle] = useState<CSSProperties>(CENTERED);

  // Posiciona el popover junto al botón que lo abrió, siempre dentro del viewport.
  useLayoutEffect(() => {
    const el = anchorRef?.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const W = 440;
    const maxHeight = Math.min(460, window.innerHeight - 24);
    const left = Math.max(8, Math.min(r.left, window.innerWidth - W - 8));
    // Debajo del botón; si no cabe, encima. Luego se fuerza dentro del viewport.
    let top = r.bottom + 8;
    if (top + maxHeight > window.innerHeight - 8) top = r.top - 8 - maxHeight;
    top = Math.max(8, Math.min(top, window.innerHeight - maxHeight - 8));
    setPanelStyle({ left, top, width: "min(440px, calc(100vw - 1rem))", maxHeight, transform: "none" });
  }, [anchorRef]);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(term.trim()), 400);
    return () => clearTimeout(t);
  }, [term]);

  const folderId = stack[stack.length - 1].id;
  const searching = debounced.length > 0;
  const query = useQuery({
    queryKey: ["drive-browse", scope, searching ? `q:${debounced}` : `f:${folderId ?? "root"}`],
    queryFn: () =>
      browseDrive(searching ? null : folderId, searching ? debounced : undefined, scope === "shared"),
  });

  const switchScope = (s: "mine" | "shared") => {
    if (s === scope) return;
    setScope(s);
    setStack([{ id: null, name: s === "shared" ? "Compartido conmigo" : "Mi unidad" }]);
    setTerm("");
    setDebounced("");
  };

  const entries = query.data ?? [];
  const folders = useMemo(() => entries.filter((e) => e.is_folder), [entries]);
  const files = useMemo(() => entries.filter((e) => !e.is_folder), [entries]);

  const enterFolder = (entry: DriveEntry) => {
    setTerm("");
    setDebounced("");
    if (searching) {
      setStack([{ id: null, name: "Mi unidad" }, { id: entry.external_id, name: entry.title }]);
    } else {
      setStack((s) => [...s, { id: entry.external_id, name: entry.title }]);
    }
  };

  const goTo = (index: number) => {
    setTerm("");
    setDebounced("");
    setStack((s) => s.slice(0, index + 1));
  };

  const toggle = (entry: DriveEntry) =>
    setSelected((sel) => {
      const next = { ...sel };
      if (next[entry.external_id]) delete next[entry.external_id];
      else next[entry.external_id] = entry;
      return next;
    });

  const selectedList = Object.values(selected);

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="fixed z-50 flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-pop"
        style={panelStyle}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Folder className="h-4 w-4 text-brand-600" /> {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="border-b border-slate-100 px-4 py-2.5">
          <div className="mb-2 inline-flex rounded-lg border border-slate-200 p-0.5 text-xs font-medium">
            {([["mine", "Mi unidad"], ["shared", "Compartido conmigo"]] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => switchScope(key)}
                className={`rounded-md px-2.5 py-1 transition ${
                  scope === key ? "bg-brand-600 text-white" : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Buscar en todo tu Drive…"
              className="h-9 w-full rounded-lg border border-slate-300 bg-white pl-8 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
          {!searching && (
            <div className="mt-2 flex flex-wrap items-center gap-0.5 text-xs text-slate-500">
              {stack.map((c, i) => (
                <span key={`${c.id ?? "root"}-${i}`} className="flex items-center">
                  {i > 0 && <ChevronRight className="h-3 w-3 text-slate-300" />}
                  <button
                    type="button"
                    onClick={() => goTo(i)}
                    className={`rounded px-1 py-0.5 transition hover:bg-slate-100 ${
                      i === stack.length - 1 ? "font-medium text-slate-700" : "text-slate-500"
                    }`}
                  >
                    {c.name}
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {query.isLoading ? (
            <div className="py-8">
              <Spinner label="Cargando Drive…" />
            </div>
          ) : query.isError ? (
            <p className="px-3 py-6 text-center text-sm text-red-600">
              {(query.error as Error).message}
            </p>
          ) : entries.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-slate-400">
              {searching ? "Sin resultados." : "Esta carpeta está vacía."}
            </p>
          ) : (
            <ul className="space-y-0.5">
              {folders.map((f) => (
                <li key={f.external_id}>
                  <button
                    type="button"
                    onClick={() => enterFolder(f)}
                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-slate-50"
                  >
                    <Folder className="h-4 w-4 shrink-0 text-amber-500" />
                    <span className="min-w-0 flex-1 truncate text-slate-700">{f.title}</span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
                  </button>
                </li>
              ))}
              {files.map((file) => {
                const isSelected = !!selected[file.external_id];
                const isPending = pendingId === file.external_id;
                return (
                  <li
                    key={file.external_id}
                    className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm hover:bg-slate-50"
                  >
                    {multiSelect && (
                      <button
                        type="button"
                        onClick={() => toggle(file)}
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                          isSelected ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300"
                        }`}
                      >
                        {isSelected && <span className="text-[10px] leading-none">✓</span>}
                      </button>
                    )}
                    {fileIcon(file.mime_type)}
                    <span className="min-w-0 flex-1 truncate text-slate-700">{file.title}</span>
                    {!multiSelect && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => onPick?.(file)}
                        className="shrink-0 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
                      >
                        {isPending ? "…" : actionLabel}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {multiSelect && (
          <div className="flex items-center justify-between gap-2 border-t border-slate-200 px-4 py-3">
            <span className="text-xs text-slate-500">{selectedList.length} seleccionados</span>
            <button
              type="button"
              disabled={busy || selectedList.length === 0}
              onClick={() => onConfirm?.(selectedList)}
              className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {busy ? "Importando…" : `${actionLabel} (${selectedList.length})`}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
