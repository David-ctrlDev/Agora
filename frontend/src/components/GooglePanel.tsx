import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, Check, Cloud, FileText, RefreshCw, Search, Video, X } from "lucide-react";
import { useState } from "react";

import {
  type GoogleDocument,
  createMeeting,
  googleStatus,
  listGoogleDocuments,
  syncGoogle,
} from "../api/google";
import { listUsers } from "../api/users";
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
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const connected = statusQuery.data?.connected ?? false;

  const [showMeeting, setShowMeeting] = useState(false);
  const [title, setTitle] = useState("");
  const [attendees, setAttendees] = useState<string[]>([]);
  const [peopleSearch, setPeopleSearch] = useState("");
  const [when, setWhen] = useState("");

  const invalidateDocs = () =>
    queryClient.invalidateQueries({ queryKey: ["project", projectId, "google-docs"] });

  const sync = useMutation({ mutationFn: () => syncGoogle(projectId), onSuccess: invalidateDocs });
  const meeting = useMutation({
    mutationFn: () => createMeeting(projectId, { title: title.trim(), attendees, when: when || null }),
    onSuccess: () => {
      invalidateDocs();
      setShowMeeting(false);
      setTitle("");
      setAttendees([]);
      setPeopleSearch("");
      setWhen("");
    },
  });

  const toggleAttendee = (email: string) =>
    setAttendees((a) => (a.includes(email) ? a.filter((x) => x !== email) : [...a, email]));

  const people = usersQuery.data ?? [];
  const q = peopleSearch.trim().toLowerCase();
  const filteredPeople = people.filter(
    (u) => !q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
  );

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
          Conecta tu cuenta de Google desde la barra lateral para crear reuniones e invitar a tu
          equipo, y traer archivos de Drive de este proyecto.
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

              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">
                  Invitados (de tu empresa)
                </label>
                {attendees.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {attendees.map((em) => (
                      <span
                        key={em}
                        className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2 py-0.5 text-xs text-brand-700"
                      >
                        {em}
                        <button type="button" onClick={() => toggleAttendee(em)} className="hover:text-red-600">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                  <input
                    value={peopleSearch}
                    onChange={(e) => setPeopleSearch(e.target.value)}
                    placeholder="Buscar persona…"
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white pl-8 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  />
                </div>
                <ul className="mt-1.5 max-h-40 overflow-y-auto rounded-lg border border-slate-200 bg-white">
                  {filteredPeople.length === 0 ? (
                    <li className="px-3 py-2 text-xs text-slate-400">Sin resultados.</li>
                  ) : (
                    filteredPeople.map((u) => {
                      const selected = attendees.includes(u.email);
                      return (
                        <li key={u.id}>
                          <button
                            type="button"
                            onClick={() => toggleAttendee(u.email)}
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-left transition hover:bg-slate-50"
                          >
                            <span
                              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${selected ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300"}`}
                            >
                              {selected && <Check className="h-3 w-3" />}
                            </span>
                            <span className="min-w-0 flex-1 truncate text-sm">
                              <span className="text-slate-800">{u.name}</span>{" "}
                              <span className="text-xs text-slate-400">{u.email}</span>
                            </span>
                          </button>
                        </li>
                      );
                    })
                  )}
                </ul>
              </div>

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
