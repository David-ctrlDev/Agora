import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import { createDocument, deleteDocument, listDocuments } from "../api/knowledge";
import { Button, Card, Input, Spinner, Textarea } from "./ui";

interface Props {
  projectId: number;
  canEdit: boolean;
}

export default function KnowledgePanel({ projectId, canEdit }: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["project", projectId, "kb"];
  const docsQuery = useQuery({ queryKey, queryFn: () => listDocuments(projectId) });

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey });
  const create = useMutation({
    mutationFn: () => createDocument(projectId, title.trim(), content.trim()),
    onSuccess: () => {
      invalidate();
      setTitle("");
      setContent("");
      setShowForm(false);
    },
  });
  const remove = useMutation({ mutationFn: deleteDocument, onSuccess: invalidate });

  const docs = docsQuery.data ?? [];

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (title.trim() && content.trim()) create.mutate();
  };

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-slate-700" />
          <h2 className="text-sm font-semibold text-slate-700">Base de conocimiento</h2>
        </div>
        {canEdit && (
          <Button
            size="sm"
            variant={showForm ? "secondary" : "primary"}
            onClick={() => setShowForm((v) => !v)}
          >
            <Plus className="h-4 w-4" /> Añadir documento
          </Button>
        )}
      </div>
      <p className="mb-4 text-xs text-slate-400">
        Los documentos se indexan (embeddings en pgvector) para que el agente responda con su
        contenido.
      </p>

      {canEdit && showForm && (
        <form onSubmit={submit} className="mb-4 space-y-3 rounded-lg border border-slate-200 p-4">
          <Input
            label="Título"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={300}
            placeholder="p. ej. Acta de reunión"
          />
          <Textarea
            label="Contenido"
            rows={5}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Pega aquí el texto del documento…"
          />
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={!title.trim() || !content.trim() || create.isPending}
            >
              {create.isPending ? "Indexando…" : "Guardar e indexar"}
            </Button>
          </div>
        </form>
      )}

      {docsQuery.isLoading ? (
        <Spinner label="Cargando…" />
      ) : docs.length === 0 ? (
        <p className="text-sm text-slate-400">Sin documentos en la base de conocimiento.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium text-slate-900">{d.title}</div>
                <div className="text-xs text-slate-400">
                  {d.source} · {new Date(d.created_at).toLocaleDateString("es-CO")}
                </div>
              </div>
              {canEdit && (
                <button
                  type="button"
                  onClick={() => remove.mutate(d.id)}
                  title="Eliminar"
                  className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
