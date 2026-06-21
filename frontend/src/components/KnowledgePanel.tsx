import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Download, Eye, FileText, Plus, Trash2, Upload } from "lucide-react";
import { type FormEvent, useRef, useState } from "react";

import {
  addDocumentVersion,
  createDocument,
  deleteDocument,
  documentDownloadUrl,
  getDocument,
  listDocuments,
  listVersions,
  uploadDocument,
  versionDownloadUrl,
} from "../api/knowledge";
import { Badge, Button, Card, Input, Modal, Select, Spinner, Textarea } from "./ui";

const SOURCE_LABEL: Record<string, string> = {
  manual: "Texto",
  file: "Archivo",
  transcript: "Transcripción",
  google_drive: "Drive",
};

const ACCEPT = ".pdf,.docx,.txt,.md,.csv,.vtt,.srt";

interface Props {
  projectId: number;
  canEdit: boolean;
}

export default function KnowledgePanel({ projectId, canEdit }: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["project", projectId, "kb"];
  const docsQuery = useQuery({ queryKey, queryFn: () => listDocuments(projectId) });
  const fileRef = useRef<HTMLInputElement>(null);

  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [source, setSource] = useState("manual");
  const [error, setError] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<number | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey });
  const create = useMutation({
    mutationFn: () => createDocument(projectId, title.trim(), content.trim(), source),
    onSuccess: () => {
      invalidate();
      setTitle("");
      setContent("");
      setShowForm(false);
    },
  });
  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(projectId, file),
    onSuccess: () => {
      invalidate();
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });
  const remove = useMutation({ mutationFn: deleteDocument, onSuccess: invalidate });

  const preview = useQuery({
    queryKey: ["document", previewId],
    queryFn: () => getDocument(previewId as number),
    enabled: previewId != null,
  });
  const versions = useQuery({
    queryKey: ["document", previewId, "versions"],
    queryFn: () => listVersions(previewId as number),
    enabled: previewId != null,
  });
  const versionFileRef = useRef<HTMLInputElement>(null);
  const addVersion = useMutation({
    mutationFn: (file: File) => addDocumentVersion(previewId as number, file),
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["document", previewId] });
      queryClient.invalidateQueries({ queryKey: ["document", previewId, "versions"] });
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const docs = docsQuery.data ?? [];

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (title.trim() && content.trim()) create.mutate();
  };

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-slate-700" />
          <h2 className="text-sm font-semibold text-slate-700">Base de conocimiento</h2>
        </div>
        {canEdit && (
          <div className="flex gap-2">
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate(file);
                e.target.value = "";
              }}
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={() => fileRef.current?.click()}
              disabled={upload.isPending}
            >
              <Upload className="h-4 w-4" /> {upload.isPending ? "Subiendo…" : "Subir archivo"}
            </Button>
            <Button
              size="sm"
              variant={showForm ? "secondary" : "primary"}
              onClick={() => setShowForm((v) => !v)}
            >
              <Plus className="h-4 w-4" /> Añadir texto
            </Button>
          </div>
        )}
      </div>
      <p className="mb-4 text-xs text-slate-400">
        Sube PDF, Word o transcripciones (o pega texto). Se indexan con embeddings para que el agente
        responda con su contenido.
      </p>

      {error && (
        <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {canEdit && showForm && (
        <form onSubmit={submit} className="mb-4 space-y-3 rounded-lg border border-slate-200 p-4">
          <Input
            label="Título"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={300}
            placeholder="p. ej. Acta de reunión"
          />
          <div className="w-56">
            <Select label="Tipo" value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="manual">Documento / nota</option>
              <option value="transcript">Transcripción de reunión</option>
            </Select>
          </div>
          <Textarea
            label="Contenido"
            rows={5}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Pega aquí el texto…"
          />
          <div className="flex justify-end">
            <Button type="submit" disabled={!title.trim() || !content.trim() || create.isPending}>
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
            <li key={d.id} className="flex items-center gap-3 py-2">
              <FileText className="h-4 w-4 shrink-0 text-slate-400" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-slate-900">{d.title}</div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Badge tone="neutral">{SOURCE_LABEL[d.source] ?? d.source}</Badge>
                  <span>{new Date(d.created_at).toLocaleDateString("es-CO")}</span>
                  {d.file_name && <span className="truncate">· {d.file_name}</span>}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setPreviewId(d.id)}
                title="Ver"
                className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <Eye className="h-4 w-4" />
              </button>
              <a
                href={documentDownloadUrl(d.id)}
                title="Descargar"
                className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <Download className="h-4 w-4" />
              </a>
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

      <Modal
        open={previewId != null}
        onClose={() => setPreviewId(null)}
        title={preview.data?.title ?? "Documento"}
      >
        {preview.isLoading ? (
          <Spinner label="Cargando…" />
        ) : (
          <div className="space-y-4">
            <pre className="max-h-[40vh] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
              {preview.data?.content_text || "Sin texto disponible."}
            </pre>
            <div className="border-t border-slate-100 pt-3">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  Versiones anteriores
                </p>
                {canEdit && (
                  <>
                    <input
                      ref={versionFileRef}
                      type="file"
                      accept={ACCEPT}
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) addVersion.mutate(file);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => versionFileRef.current?.click()}
                      disabled={addVersion.isPending}
                    >
                      <Upload className="h-4 w-4" />{" "}
                      {addVersion.isPending ? "Subiendo…" : "Nueva versión"}
                    </Button>
                  </>
                )}
              </div>
              {versions.data && versions.data.length > 0 ? (
                <ul className="space-y-1">
                  {versions.data.map((v) => (
                    <li key={v.id} className="flex items-center gap-2 text-sm">
                      <Badge tone="neutral">v{v.version_no}</Badge>
                      <span className="flex-1 truncate text-slate-600">{v.title}</span>
                      <span className="text-xs text-slate-400">
                        {new Date(v.created_at).toLocaleDateString("es-CO")}
                      </span>
                      <a
                        href={versionDownloadUrl(v.id)}
                        title="Descargar versión"
                        className="text-slate-400 transition hover:text-slate-700"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">Solo existe la versión actual.</p>
              )}
            </div>
          </div>
        )}
      </Modal>
    </Card>
  );
}
