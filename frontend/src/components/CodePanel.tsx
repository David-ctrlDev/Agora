import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Code2,
  Download,
  FileText,
  FolderUp,
  GitBranch,
  History,
  RotateCcw,
  Send,
  Shield,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { type ChangeEvent, useRef, useState } from "react";

import {
  type CommitInfo,
  branchDiff,
  createBranch,
  deleteBranch,
  getCodeStatus,
  getGitignore,
  listCommits,
  mergeBranch,
  restoreCommit,
  setGitignore,
  uploadCode,
  zipUrl,
} from "../api/code";
import { type Project, updateProject } from "../api/projects";
import { useMe } from "../auth/useAuth";
import { Badge, Button, Input, Modal, Panel, Spinner, Textarea } from "./ui";

const MAIN = "main";

function timeAgo(iso: string): string {
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return "hace un momento";
  const m = Math.floor(s / 60);
  if (m < 60) return `hace ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.floor(h / 24);
  if (d < 30) return `hace ${d} d`;
  return `hace ${Math.floor(d / 30)} mes(es)`;
}

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Algo falló, intenta de nuevo.";
}

/** Diff unificado coloreado, apto para no técnicos. */
function DiffView({ text }: { text: string }) {
  return (
    <pre className="max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed">
      {text.split("\n").map((line, i) => {
        const color = line.startsWith("+")
          ? "text-emerald-300"
          : line.startsWith("-")
            ? "text-rose-300"
            : line.startsWith("@@")
              ? "text-sky-300"
              : "text-slate-400";
        return (
          <div key={i} className={color}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

interface Props {
  project: Project;
  canEdit: boolean;
}

export default function CodePanel({ project, canEdit }: Props) {
  const me = useMe();
  const qc = useQueryClient();
  const projectId = project.id;

  const canToggle =
    me.data?.is_superadmin ||
    me.data?.areas?.some(
      (a) => a.id === project.area_id && (a.area_role === "lead" || a.area_role === "admin"),
    );

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["code-status", projectId] });
    qc.invalidateQueries({ queryKey: ["code-commits", projectId] });
  };

  const toggleDev = useMutation({
    mutationFn: (value: boolean) => updateProject(projectId, { is_development: value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", projectId] }),
  });

  const [branch, setBranch] = useState(MAIN);
  const status = useQuery({
    queryKey: ["code-status", projectId],
    queryFn: () => getCodeStatus(projectId),
    enabled: project.is_development,
  });
  const commits = useQuery({
    queryKey: ["code-commits", projectId, branch],
    queryFn: () => listCommits(projectId, branch),
    enabled: project.is_development,
  });

  // ── modales ──
  const [showUpload, setShowUpload] = useState(false);
  const [showGitignore, setShowGitignore] = useState(false);
  const [showBranch, setShowBranch] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [conflicts, setConflicts] = useState<string[] | null>(null);
  const [resolutions, setResolutions] = useState<Record<string, "draft" | "main">>({});

  // ── subir cambios ──
  const [pending, setPending] = useState<{ file: File; path: string }[]>([]);
  const [message, setMessage] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);

  const addFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const list = Array.from(e.target.files ?? []).map((f) => ({
      file: f,
      path: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name,
    }));
    setPending((prev) => {
      const seen = new Set(prev.map((p) => p.path));
      return [...prev, ...list.filter((p) => !seen.has(p.path))];
    });
    e.target.value = "";
  };

  const upload = useMutation({
    mutationFn: () => uploadCode(projectId, pending, message.trim(), branch),
    onSuccess: () => {
      invalidateAll();
      setShowUpload(false);
      setPending([]);
      setMessage("");
    },
  });

  // ── gitignore ──
  const gitignore = useQuery({
    queryKey: ["code-gitignore", projectId],
    queryFn: () => getGitignore(projectId),
    enabled: showGitignore,
  });
  const [giSelected, setGiSelected] = useState<string[] | null>(null);
  const [giExtra, setGiExtra] = useState<string | null>(null);
  const giActive =
    giSelected ??
    (gitignore.data
      ? gitignore.data.active.length
        ? gitignore.data.active
        : gitignore.data.categories.filter((c) => c.recommended).map((c) => c.id)
      : []);
  const saveGitignore = useMutation({
    mutationFn: () => setGitignore(projectId, giActive, giExtra ?? gitignore.data?.extra ?? ""),
    onSuccess: () => {
      invalidateAll();
      qc.invalidateQueries({ queryKey: ["code-gitignore", projectId] });
      setShowGitignore(false);
      setGiSelected(null);
      setGiExtra(null);
    },
  });

  // ── borradores ──
  const [branchName, setBranchName] = useState("");
  const newBranch = useMutation({
    mutationFn: () => createBranch(projectId, branchName.trim()),
    onSuccess: (r) => {
      invalidateAll();
      setShowBranch(false);
      setBranchName("");
      setBranch(r.name);
    },
  });
  const discardBranch = useMutation({
    mutationFn: () => deleteBranch(projectId, branch),
    onSuccess: () => {
      invalidateAll();
      setBranch(MAIN);
    },
  });
  const diff = useQuery({
    queryKey: ["code-diff", projectId, branch],
    queryFn: () => branchDiff(projectId, branch),
    enabled: project.is_development && branch !== MAIN && (showDiff || conflicts !== null),
  });

  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState("");
  const publish = async (withResolutions?: Record<string, "draft" | "main">) => {
    setPublishing(true);
    setPublishError("");
    try {
      const result = await mergeBranch(projectId, branch, withResolutions);
      if (result.ok) {
        setConflicts(null);
        setResolutions({});
        setShowDiff(false);
        setBranch(MAIN);
        invalidateAll();
      } else {
        setConflicts(result.conflicts);
        setResolutions(Object.fromEntries(result.conflicts.map((p) => [p, "draft" as const])));
      }
    } catch (e) {
      setPublishError(errMsg(e));
    } finally {
      setPublishing(false);
    }
  };

  const restore = useMutation({
    mutationFn: (hash: string) => restoreCommit(projectId, hash, branch),
    onSuccess: invalidateAll,
  });

  // ─────────────────── render ───────────────────

  if (!project.is_development) {
    if (!canToggle) return null;
    return (
      <Panel
        title="Código"
        subtitle="Historial de versiones para proyectos de desarrollo (Git sin comandos)"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-xl text-sm text-slate-500">
            Al activarlo, el equipo podrá subir archivos como versiones, ver qué cambió, restaurar
            cualquier versión y trabajar con borradores. Solo para proyectos de desarrollo.
          </p>
          <Button onClick={() => toggleDev.mutate(true)} disabled={toggleDev.isPending}>
            <Code2 className="h-4 w-4" />
            {toggleDev.isPending ? "Activando…" : "Activar proyecto de desarrollo"}
          </Button>
        </div>
      </Panel>
    );
  }

  const branches = status.data?.branches ?? [];
  const initialized = status.data?.initialized ?? false;
  const drafts = branches.filter((b) => !b.is_default);
  const onDraft = branch !== MAIN;
  const list = commits.data ?? [];

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-slate-400" /> Código
        </span>
      }
      subtitle="Versiones del proyecto — sube cambios, mira el historial y restaura sin comandos"
      actions={
        canEdit ? (
          <div className="flex flex-wrap items-center gap-2">
            {(drafts.length > 0 || onDraft) && (
              <select
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700"
              >
                <option value={MAIN}>Línea oficial</option>
                {drafts.map((b) => (
                  <option key={b.name} value={b.name}>
                    Borrador: {b.name}
                  </option>
                ))}
              </select>
            )}
            <Button size="sm" onClick={() => setShowUpload(true)}>
              <Upload className="h-3.5 w-3.5" /> Subir cambios
            </Button>
          </div>
        ) : undefined
      }
    >
      <div className="space-y-4">
        {/* Barra de acciones secundarias */}
        {canEdit && initialized && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setShowGitignore(true)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 font-medium text-slate-600 transition hover:bg-slate-50"
            >
              <Shield className="h-3.5 w-3.5" /> Archivos a ignorar
            </button>
            {!onDraft && (
              <button
                type="button"
                onClick={() => setShowBranch(true)}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 font-medium text-slate-600 transition hover:bg-slate-50"
              >
                <GitBranch className="h-3.5 w-3.5" /> Crear borrador
              </button>
            )}
            {onDraft && (
              <>
                <button
                  type="button"
                  onClick={() => setShowDiff(true)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 font-medium text-slate-600 transition hover:bg-slate-50"
                >
                  <FileText className="h-3.5 w-3.5" /> Comparar con la oficial
                </button>
                <button
                  type="button"
                  onClick={() => void publish()}
                  disabled={publishing}
                  className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-2.5 py-1 font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
                >
                  <Send className="h-3.5 w-3.5" /> {publishing ? "Publicando…" : "Publicar borrador"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm(`¿Descartar el borrador «${branch}» y sus cambios?`))
                      discardBranch.mutate();
                  }}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 font-medium text-red-600 transition hover:bg-red-50"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Descartar
                </button>
              </>
            )}
            {publishError && <span className="text-rose-600">{publishError}</span>}
          </div>
        )}

        {/* Historial */}
        {status.isLoading || commits.isLoading ? (
          <Spinner label="Cargando versiones…" />
        ) : !initialized ? (
          <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center">
            <History className="mx-auto h-6 w-6 text-slate-300" />
            <p className="mt-2 text-sm text-slate-500">
              Aún no hay versiones. Sube los archivos del proyecto para crear la primera.
            </p>
            {canEdit && (
              <Button className="mt-3" onClick={() => setShowUpload(true)}>
                <Upload className="h-4 w-4" /> Subir la primera versión
              </Button>
            )}
          </div>
        ) : list.length === 0 ? (
          <p className="text-sm text-slate-400">Este borrador aún no tiene cambios propios.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {list.map((commit: CommitInfo, idx) => (
              <li key={commit.hash} className="flex items-start justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-slate-800" title={commit.message}>
                      {commit.message}
                    </span>
                    {idx === 0 && <Badge tone="success">Actual</Badge>}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    {commit.author} · {timeAgo(commit.date)} ·{" "}
                    <span className="font-mono">{commit.short}</span>
                    {commit.files.length > 0 && (
                      <span title={commit.files.join("\n")}>
                        {" "}
                        · {commit.files.length} archivo{commit.files.length === 1 ? "" : "s"}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <a
                    href={zipUrl(projectId, commit.hash)}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                    title="Descargar esta versión en ZIP"
                  >
                    <Download className="h-3.5 w-3.5" /> ZIP
                  </a>
                  {canEdit && idx > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            `¿Volver a la versión «${commit.message}»?\n\nSe creará una versión nueva con ese contenido; nada se pierde.`,
                          )
                        )
                          restore.mutate(commit.hash);
                      }}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                    >
                      <RotateCcw className="h-3.5 w-3.5" /> Restaurar
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {restore.isError && <p className="text-sm text-rose-600">{errMsg(restore.error)}</p>}

        {canToggle && (
          <button
            type="button"
            onClick={() => {
              if (window.confirm("¿Desactivar la pestaña Código? Las versiones no se borran."))
                toggleDev.mutate(false);
            }}
            className="text-xs text-slate-400 underline-offset-2 hover:underline"
          >
            Desactivar proyecto de desarrollo
          </button>
        )}
      </div>

      {/* ─── Modal: subir cambios ─── */}
      <Modal open={showUpload} onClose={() => setShowUpload(false)} title="Subir cambios" size="xl">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <input ref={fileInput} type="file" multiple className="hidden" onChange={addFiles} />
            <input
              ref={folderInput}
              type="file"
              multiple
              className="hidden"
              onChange={addFiles}
              {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
            />
            <Button variant="secondary" onClick={() => fileInput.current?.click()}>
              <Upload className="h-4 w-4" /> Elegir archivos
            </Button>
            <Button variant="secondary" onClick={() => folderInput.current?.click()}>
              <FolderUp className="h-4 w-4" /> Elegir carpeta
            </Button>
            {onDraft && <Badge tone="brand">Subiendo al borrador: {branch}</Badge>}
          </div>
          {pending.length > 0 && (
            <div className="max-h-44 overflow-auto rounded-xl border border-slate-200">
              <ul className="divide-y divide-slate-100 text-xs">
                {pending.map((p) => (
                  <li key={p.path} className="flex items-center justify-between gap-2 px-3 py-1.5">
                    <span className="truncate font-mono text-slate-600">{p.path}</span>
                    <button
                      type="button"
                      onClick={() => setPending((prev) => prev.filter((x) => x.path !== p.path))}
                      className="text-slate-400 hover:text-red-600"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Textarea
            label="¿Qué cambiaste? (mensaje de la versión)"
            rows={2}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="p. ej. Corregido el cálculo de inventario y agregado el reporte PDF"
          />
          {upload.isError && <p className="text-sm text-rose-600">{errMsg(upload.error)}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowUpload(false)}>
              Cancelar
            </Button>
            <Button onClick={() => upload.mutate()} disabled={pending.length === 0 || upload.isPending}>
              {upload.isPending ? "Subiendo…" : `Subir ${pending.length} archivo(s)`}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ─── Modal: gitignore asistido ─── */}
      <Modal
        open={showGitignore}
        onClose={() => setShowGitignore(false)}
        title="Archivos a ignorar (.gitignore)"
        size="xl"
      >
        {gitignore.isLoading || !gitignore.data ? (
          <Spinner label="Cargando…" />
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-500">
              Marca qué tipos de archivo NO deben guardarse en las versiones. Ágora los excluirá
              automáticamente de las subidas futuras.
            </p>
            <div className="space-y-2">
              {gitignore.data.categories.map((cat) => (
                <label
                  key={cat.id}
                  className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 p-3 transition hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={giActive.includes(cat.id)}
                    onChange={(e) =>
                      setGiSelected(
                        e.target.checked
                          ? [...giActive, cat.id]
                          : giActive.filter((c) => c !== cat.id),
                      )
                    }
                    className="mt-0.5 h-4 w-4 accent-emerald-600"
                  />
                  <span className="min-w-0">
                    <span className="flex items-center gap-2 text-sm font-medium text-slate-800">
                      {cat.title}
                      {cat.recommended && <Badge tone="success">Recomendado</Badge>}
                    </span>
                    <span className="mt-0.5 block text-xs text-slate-500">{cat.description}</span>
                    <span className="mt-1 block truncate font-mono text-[10px] text-slate-400">
                      {cat.patterns.join("  ")}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            <Input
              label="Reglas propias (opcional, una por línea en el campo)"
              value={giExtra ?? gitignore.data.extra}
              onChange={(e) => setGiExtra(e.target.value)}
              placeholder="p. ej. *.bak"
            />
            {saveGitignore.isError && (
              <p className="text-sm text-rose-600">{errMsg(saveGitignore.error)}</p>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setShowGitignore(false)}>
                Cancelar
              </Button>
              <Button onClick={() => saveGitignore.mutate()} disabled={saveGitignore.isPending}>
                {saveGitignore.isPending ? "Guardando…" : "Guardar"}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ─── Modal: crear borrador ─── */}
      <Modal open={showBranch} onClose={() => setShowBranch(false)} title="Crear borrador" size="md">
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            Un borrador es una copia de trabajo: experimenta sin tocar la línea oficial y publícalo
            cuando esté listo.
          </p>
          <Input
            label="Nombre del borrador"
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            placeholder="p. ej. rediseño del reporte"
          />
          {newBranch.isError && <p className="text-sm text-rose-600">{errMsg(newBranch.error)}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowBranch(false)}>
              Cancelar
            </Button>
            <Button onClick={() => newBranch.mutate()} disabled={!branchName.trim() || newBranch.isPending}>
              {newBranch.isPending ? "Creando…" : "Crear"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ─── Modal: comparar borrador ─── */}
      <Modal
        open={showDiff}
        onClose={() => setShowDiff(false)}
        title={`Cambios del borrador «${branch}»`}
        size="xl"
      >
        {diff.isLoading || !diff.data ? (
          <Spinner label="Comparando…" />
        ) : diff.data.files.length === 0 ? (
          <p className="text-sm text-slate-400">El borrador no tiene diferencias con la línea oficial.</p>
        ) : (
          <div className="space-y-3">
            {diff.data.files.map((f) => (
              <div key={f.path}>
                <div className="mb-1 flex items-center gap-2 text-xs">
                  <Badge tone={f.status === "A" ? "success" : f.status === "D" ? "danger" : "brand"}>
                    {f.status === "A" ? "Nuevo" : f.status === "D" ? "Eliminado" : "Modificado"}
                  </Badge>
                  <span className="truncate font-mono text-slate-600">{f.path}</span>
                </div>
                {diff.data.diffs[f.path] ? (
                  <DiffView text={diff.data.diffs[f.path]} />
                ) : (
                  <p className="text-xs text-slate-400">
                    {diff.data.binary.includes(f.path) ? "Archivo binario (sin vista de diferencias)." : ""}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* ─── Modal: resolver conflictos al publicar ─── */}
      <Modal
        open={conflicts !== null}
        onClose={() => setConflicts(null)}
        title="Estos archivos cambiaron en ambos lados"
        size="xl"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            Mientras trabajabas en el borrador, la línea oficial también cambió estos archivos. Elige
            cuál versión vale para cada uno — la otra queda en el historial, nada se pierde.
          </p>
          <div className="space-y-3">
            {(conflicts ?? []).map((path) => (
              <div key={path} className="rounded-xl border border-slate-200 p-3">
                <div className="mb-2 truncate font-mono text-xs text-slate-700">{path}</div>
                <div className="flex flex-wrap gap-3 text-sm">
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input
                      type="radio"
                      name={`res-${path}`}
                      checked={resolutions[path] === "draft"}
                      onChange={() => setResolutions((r) => ({ ...r, [path]: "draft" }))}
                      className="accent-emerald-600"
                    />
                    Usar la del borrador
                  </label>
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input
                      type="radio"
                      name={`res-${path}`}
                      checked={resolutions[path] === "main"}
                      onChange={() => setResolutions((r) => ({ ...r, [path]: "main" }))}
                      className="accent-emerald-600"
                    />
                    Mantener la oficial
                  </label>
                </div>
                {diff.data?.diffs[path] && <div className="mt-2"><DiffView text={diff.data.diffs[path]} /></div>}
              </div>
            ))}
          </div>
          {publishError && <p className="text-sm text-rose-600">{publishError}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConflicts(null)}>
              Cancelar
            </Button>
            <Button onClick={() => void publish(resolutions)} disabled={publishing}>
              {publishing ? "Publicando…" : "Publicar con estas decisiones"}
            </Button>
          </div>
        </div>
      </Modal>
    </Panel>
  );
}
