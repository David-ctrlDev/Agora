import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, Cloud, FileText, RefreshCw, Video } from "lucide-react";
import { useState } from "react";

import {
  type GoogleDocument,
  createMeeting,
  googleStatus,
  listGoogleDocuments,
  syncGoogle,
} from "../api/google";
import { Badge, Button, Card, Input, Spinner } from "./ui";

interface Props {
  projectId: number;
  canEdit: boolean;
}

function DocList({ docs }: { docs: GoogleDocument[] }) {
  if (docs.length === 0) return <li className="text-xs text-slate-400">—</li>;
  return (
    <>
      {docs.map((d) => (
        <li key={d.id} className="text-sm">
          <a
            href={d.web_url ?? "#"}
            target="_blank"
            rel="noreferrer"
            className="text-slate-800 transition hover:text-brand-600"
          >
            {d.title}
          </a>
          {d.occurred_at && (
            <span className="block text-xs text-slate-400">
              {new Date(d.occurred_at).toLocaleDateString("es-CO")}
            </span>
          )}
        </li>
      ))}
    </>
  );
}

export default function GooglePanel({ projectId, canEdit }: Props) {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ["google-status"], queryFn: googleStatus });
  const docsQuery = useQuery({
    queryKey: ["project", projectId, "google-docs"],
    queryFn: () => listGoogleDocuments(projectId),
  });
  const connected = statusQuery.data?.connected ?? false;

  const [showMeeting, setShowMeeting] = useState(false);
  const [title, setTitle] = useState("");
  const [attendees, setAttendees] = useState("");
  const [when, setWhen] = useState("");

  const invalidateDocs = () =>
    queryClient.invalidateQueries({ queryKey: ["project", projectId, "google-docs"] });

  const sync = useMutation({ mutationFn: () => syncGoogle(projectId), onSuccess: invalidateDocs });
  const meeting = useMutation({
    mutationFn: () =>
      createMeeting(projectId, {
        title: title.trim(),
        attendees: attendees
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        when: when || null,
      }),
    onSuccess: () => {
      invalidateDocs();
      setShowMeeting(false);
      setTitle("");
      setAttendees("");
      setWhen("");
    },
  });

  const docs = docsQuery.data ?? [];
  const drive = docs.filter((d) => d.source === "drive");
  const calendar = docs.filter((d) => d.source === "calendar");

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Cloud className="h-5 w-5 text-slate-700" />
          <h2 className="text-sm font-semibold text-slate-700">Google Workspace</h2>
        </div>
        <Badge tone={connected ? "success" : "neutral"}>
          {connected ? "Conectado" : "Sin conectar"}
        </Badge>
      </div>

      {!connected ? (
        <p className="text-sm text-slate-400">
          Conecta tu cuenta de Google desde la barra lateral para crear reuniones y traer archivos
          de Drive de este proyecto.
        </p>
      ) : (
        <>
          {canEdit && (
            <div className="mb-4 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => setShowMeeting((s) => !s)}>
                <Video className="h-4 w-4" /> Crear reunión
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => sync.mutate()}
                disabled={sync.isPending}
              >
                <RefreshCw className="h-4 w-4" />
                {sync.isPending ? "Trayendo…" : "Traer datos de Drive"}
              </Button>
            </div>
          )}

          {meeting.isSuccess && meeting.data && (
            <div className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              ✅ Reunión «{meeting.data.title}» creada.{" "}
              {meeting.data.meet_url && (
                <a
                  href={meeting.data.meet_url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium underline"
                >
                  Abrir en Meet
                </a>
              )}
            </div>
          )}

          {showMeeting && canEdit && (
            <div className="mb-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <Input
                label="Título"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Reunión de seguimiento"
                maxLength={200}
              />
              <Input
                label="Invitados (correos separados por coma)"
                value={attendees}
                onChange={(e) => setAttendees(e.target.value)}
                placeholder="ana@invesa.com, carlos@invesa.com"
              />
              <Input label="Fecha" type="date" value={when} onChange={(e) => setWhen(e.target.value)} />
              <div className="flex justify-end gap-2">
                <Button size="sm" variant="ghost" onClick={() => setShowMeeting(false)}>
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  onClick={() => meeting.mutate()}
                  disabled={!title.trim() || meeting.isPending}
                >
                  {meeting.isPending ? "Creando…" : "Crear reunión"}
                </Button>
              </div>
              {meeting.isError && (
                <p className="text-sm text-red-600">{(meeting.error as Error).message}</p>
              )}
            </div>
          )}

          {docsQuery.isLoading ? (
            <Spinner label="Cargando…" />
          ) : docs.length === 0 ? (
            <p className="text-sm text-slate-400">
              Sin documentos. Usa «Traer datos de Drive» para sincronizar archivos y eventos.
            </p>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <FileText className="h-3.5 w-3.5" /> Drive
                </h3>
                <ul className="space-y-2">
                  <DocList docs={drive} />
                </ul>
              </div>
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <Calendar className="h-3.5 w-3.5" /> Calendar
                </h3>
                <ul className="space-y-2">
                  <DocList docs={calendar} />
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
