import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, Clock, Cloud, FileText, FolderOpen, Plus, Users, Video, X } from "lucide-react";
import { useRef, useState } from "react";

import {
  type DriveEntry,
  type GoogleDocument,
  createMeeting,
  freeBusy,
  getDirectory,
  googleStatus,
  importDriveFiles,
  listGoogleDocuments,
} from "../api/google";
import DriveBrowser from "./DriveBrowser";
import { Badge, Button, Card, Input, Spinner } from "./ui";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const hhmm = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });

interface Props {
  projectId: number;
  canEdit: boolean;
}

function fmtWhen(iso: string, withTime: boolean): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "2-digit" });
  if (!withTime || (d.getHours() === 0 && d.getMinutes() === 0)) return date;
  return `${date} · ${d.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}`;
}

function DocList({ docs, withTime = false }: { docs: GoogleDocument[]; withTime?: boolean }) {
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
            <span className="block text-xs text-slate-400">{fmtWhen(d.occurred_at, withTime)}</span>
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
  const directoryQuery = useQuery({ queryKey: ["google-directory"], queryFn: getDirectory });
  const connected = statusQuery.data?.connected ?? false;

  const [showMeeting, setShowMeeting] = useState(false);
  const [showDrive, setShowDrive] = useState(false);
  const driveBtnRef = useRef<HTMLButtonElement>(null);

  const [title, setTitle] = useState("");
  const [attendees, setAttendees] = useState<string[]>([]);
  const [attendeeInput, setAttendeeInput] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");

  const invalidateDocs = () =>
    queryClient.invalidateQueries({ queryKey: ["project", projectId, "google-docs"] });

  const importMut = useMutation({
    mutationFn: (files: DriveEntry[]) => importDriveFiles(projectId, files),
    onSuccess: () => {
      invalidateDocs();
      setShowDrive(false);
    },
  });
  const meeting = useMutation({
    mutationFn: () =>
      createMeeting(projectId, {
        title: title.trim(),
        attendees,
        // Construimos el instante en la zona local del navegador y lo enviamos como
        // UTC (ISO con Z): así "15:00" del usuario es 15:00 SU hora, no 15:00 UTC.
        when: date ? new Date(`${date}T${time || "15:00"}`).toISOString() : null,
      }),
    onSuccess: () => {
      invalidateDocs();
      setShowMeeting(false);
      setTitle("");
      setAttendees([]);
      setAttendeeInput("");
      setDate("");
      setTime("");
    },
  });

  const dayStart = date ? new Date(`${date}T00:00:00`).toISOString() : "";
  const dayEnd = date ? new Date(`${date}T23:59:59`).toISOString() : "";
  const availability = useQuery({
    queryKey: ["freebusy", date, attendees.join(",")],
    queryFn: () => freeBusy(attendees, dayStart, dayEnd),
    enabled: showMeeting && connected && !!date && attendees.length > 0,
  });

  const addAttendee = (email: string) => {
    const e = email.trim().toLowerCase();
    if (e && !attendees.includes(e)) setAttendees((a) => [...a, e]);
    setAttendeeInput("");
  };
  const removeAttendee = (email: string) => setAttendees((a) => a.filter((x) => x !== email));

  const people = directoryQuery.data ?? [];
  const directoryEmails = new Set(people.map((u) => u.email.toLowerCase()));
  const q = attendeeInput.trim().toLowerCase();
  const matches = people
    .filter((u) => !attendees.includes(u.email) && (!q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)))
    .slice(0, 6);
  const canAddExternal = EMAIL_RE.test(q) && !attendees.includes(q) && !directoryEmails.has(q);

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
              <Button ref={driveBtnRef} size="sm" variant="secondary" onClick={() => setShowDrive(true)}>
                <FolderOpen className="h-4 w-4" /> Explorar Drive
              </Button>
            </div>
          )}

          {showDrive && (
            <DriveBrowser
              title="Importar archivos de Drive"
              actionLabel="Importar"
              multiSelect
              anchorRef={driveBtnRef}
              busy={importMut.isPending}
              onClose={() => setShowDrive(false)}
              onConfirm={(files) => importMut.mutate(files)}
            />
          )}

          {importMut.isSuccess && importMut.data && (
            <div className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              ✅ {importMut.data.new_documents} archivo(s) vinculados
              {importMut.data.indexed > 0 && ` · ${importMut.data.indexed} indizados para el agente`}.
            </div>
          )}

          {meeting.isSuccess && meeting.data && (
            <div className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              ✅ Reunión «{meeting.data.title}» creada para el {fmtWhen(meeting.data.starts_at, true)}.{" "}
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
            <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
              <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
                <Calendar className="h-4 w-4 text-brand-600" />
                <span className="text-sm font-semibold text-slate-800">Nueva reunión</span>
                <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-400">
                  <Video className="h-3.5 w-3.5" /> con enlace de Meet
                </span>
              </div>

              <div className="space-y-3.5 p-4">
                <Input
                  label="Título"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Reunión de seguimiento"
                  maxLength={200}
                />

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700">
                      <Calendar className="h-3.5 w-3.5 text-slate-400" /> Fecha
                    </label>
                    <input
                      type="date"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                      className="h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700">
                      <Clock className="h-3.5 w-3.5 text-slate-400" /> Hora
                    </label>
                    <input
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      className="h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700">
                    <Users className="h-3.5 w-3.5 text-slate-400" /> Invitados
                  </label>
                  {attendees.length > 0 && (
                    <div className="mb-2 flex flex-wrap gap-1.5">
                      {attendees.map((em) => (
                        <span
                          key={em}
                          className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700"
                        >
                          {em}
                          {!directoryEmails.has(em) && <span className="text-[10px] text-brand-400">· externo</span>}
                          <button type="button" onClick={() => removeAttendee(em)} className="hover:text-red-600">
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  <input
                    value={attendeeInput}
                    onChange={(e) => setAttendeeInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && canAddExternal) {
                        e.preventDefault();
                        addAttendee(q);
                      }
                    }}
                    placeholder="Nombre o correo (también externos)…"
                    className="h-10 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  />
                  {q.length > 0 && (matches.length > 0 || canAddExternal) && (
                    <ul className="mt-1.5 max-h-44 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                      {matches.map((u) => (
                        <li key={u.email}>
                          <button
                            type="button"
                            onClick={() => addAttendee(u.email)}
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-left transition hover:bg-slate-50"
                          >
                            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-500">
                              {u.name.slice(0, 2).toUpperCase()}
                            </span>
                            <span className="min-w-0 flex-1 truncate text-sm">
                              <span className="text-slate-800">{u.name}</span>{" "}
                              <span className="text-xs text-slate-400">{u.email}</span>
                            </span>
                          </button>
                        </li>
                      ))}
                      {canAddExternal && (
                        <li>
                          <button
                            type="button"
                            onClick={() => addAttendee(q)}
                            className="flex w-full items-center gap-2 border-t border-slate-100 px-3 py-2 text-left text-sm text-brand-700 transition hover:bg-brand-50"
                          >
                            <Plus className="h-4 w-4" /> Agregar externo «{q}»
                          </button>
                        </li>
                      )}
                    </ul>
                  )}
                  <p className="mt-1 text-xs text-slate-400">
                    Escribe un correo y pulsa Enter para invitar a alguien externo a la empresa.
                  </p>
                </div>

                {date && attendees.length > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-600">
                      <Clock className="h-3.5 w-3.5 text-slate-400" /> Disponibilidad ese día
                    </div>
                    {availability.isLoading ? (
                      <p className="text-xs text-slate-400">Consultando calendarios…</p>
                    ) : availability.isError ? (
                      <p className="text-xs text-amber-600">
                        No se pudo leer la disponibilidad. Reconecta Google para conceder el permiso de calendarios.
                      </p>
                    ) : (
                      <ul className="space-y-1.5">
                        {attendees.map((em) => {
                          const busy = availability.data?.[em] ?? [];
                          return (
                            <li key={em} className="flex items-start justify-between gap-3 text-xs">
                              <span className="min-w-0 flex-1 truncate text-slate-600">{em}</span>
                              {busy.length === 0 ? (
                                <span className="shrink-0 font-medium text-emerald-600">Libre</span>
                              ) : (
                                <span className="shrink-0 text-right text-slate-500">
                                  Ocupado {busy.map((b) => `${hhmm(b.start)}–${hhmm(b.end)}`).join(", ")}
                                </span>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                )}

                <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
                  <Button size="sm" variant="ghost" onClick={() => setShowMeeting(false)}>
                    Cancelar
                  </Button>
                  <Button size="sm" onClick={() => meeting.mutate()} disabled={!title.trim() || meeting.isPending}>
                    {meeting.isPending ? "Creando…" : "Crear reunión"}
                  </Button>
                </div>
                {meeting.isError && (
                  <p className="text-sm text-red-600">{(meeting.error as Error).message}</p>
                )}
              </div>
            </div>
          )}

          {docsQuery.isLoading ? (
            <Spinner label="Cargando…" />
          ) : docs.length === 0 ? (
            <p className="text-sm text-slate-400">
              Sin documentos. Usa «Explorar Drive» para navegar tus carpetas e importar archivos.
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
                  <DocList docs={calendar} withTime />
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
