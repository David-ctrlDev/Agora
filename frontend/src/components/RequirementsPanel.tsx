import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Paperclip, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";

import { type Project, updateProject } from "../api/projects";
import { type TaskProposal, acceptProposals, proposeTasks } from "../api/requirements";
import { TASK_PRIORITY } from "../api/tasks";
import { Badge, Button, Modal, Panel, Textarea } from "./ui";

interface Props {
  project: Project;
  canEdit: boolean;
}

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Algo falló, intenta de nuevo.";
}

/** Levantamiento de requerimientos + tareas propuestas por IA (el humano acepta). */
export default function RequirementsPanel({ project, canEdit }: Props) {
  const qc = useQueryClient();
  const [text, setText] = useState<string | null>(null);
  const value = text ?? project.requirements ?? "";
  const dirty = text !== null && text !== (project.requirements ?? "");

  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [proposals, setProposals] = useState<TaskProposal[] | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const save = useMutation({
    mutationFn: () => updateProject(project.id, { requirements: value.trim() || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", project.id] });
      setText(null);
    },
  });

  const propose = useMutation({
    mutationFn: async () => {
      // Guarda primero lo digitado para que la IA lea la versión vigente.
      if (dirty) await updateProject(project.id, { requirements: value.trim() || null });
      return proposeTasks(project.id, file);
    },
    onSuccess: (rows) => {
      qc.invalidateQueries({ queryKey: ["project", project.id] });
      setText(null);
      setProposals(rows);
      setSelected(new Set(rows.map((_, i) => i)));
    },
  });

  const accept = useMutation({
    mutationFn: () => acceptProposals(project.id, (proposals ?? []).filter((_, i) => selected.has(i))),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", project.id, "tasks", false] });
      setProposals(null);
      setFile(null);
    },
  });

  const hasContent = value.trim().length >= 20 || file !== null;

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-400" /> Requerimientos
        </span>
      }
      subtitle="Levantamiento inicial del proyecto — digítalo o adjunta un documento, y deja que la IA proponga las tareas"
    >
      <div className="space-y-3">
        <Textarea
          rows={5}
          value={value}
          onChange={(e) => setText(e.target.value)}
          disabled={!canEdit}
          placeholder={
            "Describe qué se necesita: objetivos, alcance, entregables…\n" +
            "p. ej.\n- Formulario de captura de datos de bodega\n- Validación de inventario contra SAP\n- Reporte PDF mensual para gerencia"
          }
        />
        {canEdit && (
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant="secondary" onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
              {save.isPending ? "Guardando…" : "Guardar"}
            </Button>
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <Button size="sm" variant="secondary" onClick={() => fileInput.current?.click()}>
              <Paperclip className="h-3.5 w-3.5" /> Adjuntar documento
            </Button>
            {file && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                {file.name}
                <button type="button" onClick={() => setFile(null)} className="text-slate-400 hover:text-red-600">
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
            <Button size="sm" onClick={() => propose.mutate()} disabled={!hasContent || propose.isPending}>
              <Sparkles className="h-3.5 w-3.5" />
              {propose.isPending ? "Analizando…" : "Proponer tareas con IA"}
            </Button>
          </div>
        )}
        {(save.isError || propose.isError) && (
          <p className="text-sm text-rose-600">{errMsg(save.error ?? propose.error)}</p>
        )}
      </div>

      {/* Modal: propuestas de la IA */}
      <Modal
        open={proposals !== null}
        onClose={() => setProposals(null)}
        title="Tareas propuestas por la IA"
        size="xl"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            Marca cuáles crear. Los responsables y las fechas los asignas tú después en el tablero.
          </p>
          <div className="max-h-[50vh] space-y-2 overflow-auto pr-1">
            {(proposals ?? []).map((p, i) => (
              <label
                key={i}
                className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 p-3 transition hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={selected.has(i)}
                  onChange={(e) =>
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (e.target.checked) next.add(i);
                      else next.delete(i);
                      return next;
                    })
                  }
                  className="mt-0.5 h-4 w-4 accent-emerald-600"
                />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2 text-sm font-medium text-slate-800">
                    {p.title}
                    <Badge tone={TASK_PRIORITY[p.priority]?.tone ?? "neutral"}>
                      {TASK_PRIORITY[p.priority]?.label ?? p.priority}
                    </Badge>
                  </span>
                  {p.description && (
                    <span className="mt-0.5 block text-xs text-slate-500">{p.description}</span>
                  )}
                </span>
              </label>
            ))}
          </div>
          {accept.isError && <p className="text-sm text-rose-600">{errMsg(accept.error)}</p>}
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-slate-400">
              {selected.size} de {(proposals ?? []).length} seleccionadas
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setProposals(null)}>
                Cancelar
              </Button>
              <Button onClick={() => accept.mutate()} disabled={selected.size === 0 || accept.isPending}>
                {accept.isPending ? "Creando…" : `Crear ${selected.size} tarea(s)`}
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </Panel>
  );
}
