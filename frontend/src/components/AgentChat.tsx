import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlarmClock,
  ArrowUp,
  ArrowUpRight,
  BarChart3,
  CalendarPlus,
  Check,
  ChevronDown,
  FileText,
  FolderOpen,
  ListTodo,
  MessagesSquare,
  PackageCheck,
  Paperclip,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { type ChangeEvent, type ComponentType, type KeyboardEvent, useEffect, useRef, useState } from "react";

import {
  type AgentMessage,
  type Attachment,
  attachFromDrive,
  cancelAction,
  confirmAction,
  createConversation,
  deleteAttachment,
  deleteConversation,
  listAttachments,
  listConversations,
  listMessages,
  sendMessage,
  uploadAttachment,
} from "../api/agent";
import { googleStatus } from "../api/google";
import { useMe } from "../auth/useAuth";
import { useAgentStore } from "../store/agentStore";
import AgoraMark from "./AgoraMark";
import DriveBrowser from "./DriveBrowser";
import Markdown from "./Markdown";
import { Spinner } from "./ui";

const UPLOAD_ACCEPT = ".pdf,.doc,.docx,.txt,.md,.csv,.vtt,.srt,.log";

const SUGGESTIONS: { icon: ComponentType<{ className?: string }>; text: string }[] = [
  { icon: BarChart3, text: "¿Cómo van mis proyectos?" },
  { icon: ListTodo, text: "¿Qué tareas tengo pendientes?" },
  { icon: AlarmClock, text: "¿Qué se vence esta semana?" },
  { icon: PackageCheck, text: "¿Qué proyectos entregamos pronto?" },
  { icon: CalendarPlus, text: "Agenda una reunión mañana a las 10" },
];

/** Etiqueta editorial que precede cada turno del asistente (sustituye al avatar). */
function AssistantLabel() {
  return (
    <div className="mb-1.5 flex items-center gap-2">
      <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-700/70">
        Ágora
      </span>
      <span className="h-px flex-1 bg-gradient-to-r from-brand-200/70 to-transparent" />
    </div>
  );
}

function Thinking() {
  return (
    <div className="animate-fade-in">
      <AssistantLabel />
      <div className="border-l-2 border-brand-400/40 pl-3.5">
        <span className="animate-shimmer bg-[linear-gradient(90deg,#cbd5e1_0%,#94a3b8_30%,#059669_50%,#94a3b8_70%,#cbd5e1_100%)] bg-[length:200%_100%] bg-clip-text text-sm font-medium text-transparent">
          Pensando…
        </span>
      </div>
    </div>
  );
}

function MessageRow({
  message,
  onConfirm,
  onCancel,
  busy,
}: {
  message: AgentMessage;
  onConfirm: () => void;
  onCancel: () => void;
  busy: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="flex animate-fade-in justify-end">
        <div className="max-w-[82%] whitespace-pre-wrap rounded-[20px] rounded-br-md bg-slate-900 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  const status = message.action?.status;
  return (
    <div className="animate-fade-in">
      <AssistantLabel />
      <div className="border-l-2 border-brand-400/40 pl-3.5 text-[15px] leading-relaxed text-slate-700">
        <Markdown diagramsSaveable>{message.content}</Markdown>
        {status === "pending" && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onConfirm}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-xl bg-brand-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" /> Confirmar y ejecutar
            </button>
            <button
              type="button"
              onClick={onCancel}
              disabled={busy}
              className="rounded-xl px-3 py-2 text-xs font-medium text-slate-500 transition hover:bg-slate-100 disabled:opacity-50"
            >
              Descartar
            </button>
          </div>
        )}
        {status === "executed" && (
          <div className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
            <Check className="h-3.5 w-3.5" /> Acción ejecutada
          </div>
        )}
        {status === "cancelled" && <p className="mt-2 text-xs text-slate-400">Acción descartada</p>}
      </div>
    </div>
  );
}

export default function AgentChat({ className = "" }: { className?: string }) {
  const queryClient = useQueryClient();
  const me = useMe();
  const firstName = me.data?.name?.split(" ")[0];
  const conversationId = useAgentStore((s) => s.activeConversationId);
  const setConversationId = useAgentStore((s) => s.setActiveConversationId);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<{ text: string; files: string[] } | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [showDrive, setShowDrive] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const driveBtnRef = useRef<HTMLButtonElement>(null);
  const didInit = useRef(false);

  const conversationsQuery = useQuery({ queryKey: ["agent-convs"], queryFn: listConversations });
  const googleQuery = useQuery({ queryKey: ["google-status"], queryFn: googleStatus });
  const driveConnected = googleQuery.data?.connected ?? false;
  const contextDocsQuery = useQuery({
    queryKey: ["agent-attachments", conversationId],
    queryFn: () => listAttachments(conversationId as number),
    enabled: conversationId !== null,
  });

  // Al abrir por primera vez, retomamos la conversación más reciente. Pero solo
  // una vez: si el usuario pulsa «Nuevo» (id = null) dejamos ver el inicio en
  // blanco en vez de volver a saltar a la última conversación.
  useEffect(() => {
    if (
      !didInit.current &&
      conversationId === null &&
      conversationsQuery.data &&
      conversationsQuery.data.length > 0
    ) {
      didInit.current = true;
      setConversationId(conversationsQuery.data[0].id);
    }
  }, [conversationId, conversationsQuery.data, setConversationId]);

  const messagesQuery = useQuery({
    queryKey: ["agent-msgs", conversationId],
    queryFn: () => listMessages(conversationId as number),
    enabled: conversationId !== null,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["agent-msgs"] });

  const ensureConversation = async (): Promise<number> => {
    if (conversationId !== null) return conversationId;
    const conversation = await createConversation();
    didInit.current = true;
    setConversationId(conversation.id);
    void queryClient.invalidateQueries({ queryKey: ["agent-convs"] });
    return conversation.id;
  };

  const send = useMutation({
    mutationFn: async (content: string) => {
      const cid = await ensureConversation();
      return sendMessage(cid, content, attachments.map((a) => a.id));
    },
    onSuccess: async () => {
      setAttachments([]);
      // Esperamos a que el historial se recargue antes de quitar el mensaje
      // optimista, para que no parpadee ni "salte".
      await queryClient.invalidateQueries({ queryKey: ["agent-msgs"] });
      void queryClient.invalidateQueries({ queryKey: ["agent-attachments"] });
      setPending(null);
    },
    onError: () => setPending(null),
  });

  const submit = (content: string) => {
    setPending({ text: content, files: attachments.map((a) => a.name) });
    send.mutate(content);
  };

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const cid = await ensureConversation();
      return uploadAttachment(cid, file);
    },
    onSuccess: (att) => {
      setAttachments((a) => [...a, att]);
      void queryClient.invalidateQueries({ queryKey: ["agent-attachments"] });
    },
  });

  const attachDrive = useMutation({
    mutationFn: async (fileId: string) => {
      const cid = await ensureConversation();
      return attachFromDrive(cid, fileId);
    },
    onSuccess: (att) => {
      setAttachments((a) => [...a, att]);
      setShowDrive(false);
      void queryClient.invalidateQueries({ queryKey: ["agent-attachments"] });
    },
  });

  const removeAttachment = useMutation({
    mutationFn: deleteAttachment,
    onSuccess: (_data, id) => {
      setAttachments((a) => a.filter((x) => x.id !== id));
      void queryClient.invalidateQueries({ queryKey: ["agent-attachments"] });
    },
  });

  const attaching = upload.isPending || attachDrive.isPending;
  const attachError = (upload.error || attachDrive.error) as Error | null;

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
    e.target.value = "";
  };
  // Tras ejecutar una acción del agente, refrescamos todo (tareas, proyectos,
  // analítica, inicio…) para que el cambio se vea sin recargar.
  const confirm = useMutation({
    mutationFn: confirmAction,
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const cancel = useMutation({ mutationFn: cancelAction, onSuccess: invalidate });

  const [historyOpen, setHistoryOpen] = useState(false);
  const conversations = conversationsQuery.data ?? [];
  const currentTitle =
    conversations.find((c) => c.id === conversationId)?.title ?? "Nueva conversación";
  const del = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: ["agent-convs"] });
      if (id === conversationId) setConversationId(null);
    },
  });
  const newChat = () => {
    didInit.current = true; // evita que el efecto vuelva a saltar a la última conversación
    setConversationId(null);
    setHistoryOpen(false);
    setInput("");
  };

  useEffect(() => {
    // Llevamos al fondo el PROPIO contenedor (no scrollIntoView, que recorre los
    // ancestros y, al dispararse varias veces seguidas, hacía "temblar" el panel).
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messagesQuery.data, send.isPending, pending]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }, [input]);

  const doSend = () => {
    const text = input.trim();
    if (send.isPending || attaching) return;
    if (!text && attachments.length === 0) return;
    const content =
      text || "Resume el/los documento(s) adjunto(s) y dime qué puedo hacer con ellos.";
    setInput("");
    submit(content);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      doSend();
    }
  };

  const messages = messagesQuery.data ?? [];
  const loadingHistory = conversationId !== null && messagesQuery.isLoading;
  const showEmpty = !loadingHistory && messages.length === 0 && !send.isPending;
  const canSend = (input.trim().length > 0 || attachments.length > 0) && !send.isPending && !attaching;

  // Documentos que ya viven en la conversación (el agente los conserva en contexto),
  // sin duplicar por nombre y excluyendo los que estás adjuntando ahora mismo.
  const stagedNames = new Set(attachments.map((a) => a.name));
  const contextDocs: Attachment[] = [];
  const seenDocNames = new Set<string>();
  for (const a of contextDocsQuery.data ?? []) {
    if (stagedNames.has(a.name) || seenDocNames.has(a.name)) continue;
    seenDocNames.add(a.name);
    contextDocs.push(a);
  }

  return (
    <div className={`flex min-h-0 flex-col bg-white ${className}`}>
      {/* Barra de conversación */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-200/80 px-3 py-2">
        <div className="relative min-w-0">
          <button
            type="button"
            onClick={() => setHistoryOpen((o) => !o)}
            className="flex max-w-full items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-slate-600 transition hover:bg-slate-100"
          >
            <MessagesSquare className="h-4 w-4 shrink-0 text-slate-400" />
            <span className="truncate">{currentTitle}</span>
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          </button>
          {historyOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setHistoryOpen(false)} />
              <div className="absolute left-0 top-full z-20 mt-1 max-h-72 w-72 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-1.5 shadow-pop">
                {conversations.length === 0 ? (
                  <p className="px-3 py-2 text-sm text-slate-400">Aún no hay conversaciones.</p>
                ) : (
                  conversations.map((c) => (
                    <div
                      key={c.id}
                      className={`group flex items-center gap-1 rounded-xl ${
                        c.id === conversationId ? "bg-brand-50" : "hover:bg-slate-50"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setConversationId(c.id);
                          setHistoryOpen(false);
                        }}
                        className="min-w-0 flex-1 px-2.5 py-1.5 text-left"
                      >
                        <div className="truncate text-sm text-slate-700">{c.title}</div>
                        <div className="text-xs text-slate-400">
                          {new Date(c.created_at).toLocaleDateString("es-CO", {
                            day: "2-digit",
                            month: "short",
                          })}
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => del.mutate(c.id)}
                        title="Eliminar conversación"
                        className="mr-1 rounded-lg p-1 text-slate-300 opacity-0 transition hover:text-red-600 group-hover:opacity-100"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={newChat}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-sm font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
        >
          <Plus className="h-4 w-4" /> Nuevo
        </button>
      </div>

      {/* Transcripción */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5">
        {loadingHistory ? (
          <Spinner label="Cargando…" />
        ) : showEmpty ? (
          <div className="relative flex h-full flex-col items-center justify-center px-2 text-center">
            <div
              aria-hidden
              className="pointer-events-none absolute left-1/2 top-1/4 h-44 w-44 -translate-x-1/2 rounded-full bg-brand-400/20 blur-3xl"
            />
            <AgoraMark className="relative h-14 w-14 shadow-[0_10px_30px_-8px_rgba(5,150,105,0.6)]" />
            <h3 className="relative mt-4 text-lg font-semibold tracking-tight text-slate-900">
              {firstName ? `Hola, ${firstName}` : "Hola"}
            </h3>
            <p className="relative mt-1 max-w-xs text-sm text-slate-500">
              Soy Ágora. Pregúntame por proyectos, tareas, riesgos o entregas — o pídeme una acción.
            </p>
            <div className="relative mt-6 grid w-full max-w-md gap-2">
              {SUGGESTIONS.map(({ icon: Icon, text }) => (
                <button
                  key={text}
                  type="button"
                  onClick={() => submit(text)}
                  className="group flex items-center gap-3 rounded-xl border border-slate-200/80 bg-white px-3.5 py-2.5 text-left transition hover:border-brand-300 hover:bg-brand-50/50 hover:shadow-soft"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition group-hover:bg-brand-100 group-hover:text-brand-700">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="text-sm text-slate-700">{text}</span>
                  <ArrowUpRight className="ml-auto h-4 w-4 text-slate-300 transition group-hover:text-brand-500" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-3xl space-y-5">
            {messages.map((m) => (
              <MessageRow
                key={m.id}
                message={m}
                onConfirm={() => m.action && confirm.mutate(m.action.id)}
                onCancel={() => m.action && cancel.mutate(m.action.id)}
                busy={confirm.isPending || cancel.isPending}
              />
            ))}
            {pending && (
              <div className="flex animate-fade-in justify-end">
                <div className="max-w-[82%] space-y-1">
                  <div className="whitespace-pre-wrap rounded-[20px] rounded-br-md bg-slate-900 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
                    {pending.text}
                  </div>
                  {pending.files.length > 0 && (
                    <div className="flex flex-wrap justify-end gap-1">
                      {pending.files.map((f) => (
                        <span
                          key={f}
                          className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500"
                        >
                          <FileText className="h-3 w-3" /> {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            {send.isPending && <Thinking />}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-slate-200/80 bg-slate-50/60 px-4 py-3">
        <div className="mx-auto w-full max-w-3xl">
          {contextDocs.length > 0 && (
            <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400">
              <Paperclip className="h-3 w-3 shrink-0" />
              <span className="font-medium">En contexto:</span>
              {contextDocs.map((d) => (
                <span
                  key={d.id}
                  className="inline-flex max-w-[200px] items-center gap-1 rounded-md bg-slate-100 px-1.5 py-0.5 text-slate-500"
                  title={`${d.name} · el agente recuerda este documento en esta conversación`}
                >
                  <FileText className="h-3 w-3 shrink-0" />
                  <span className="truncate">{d.name}</span>
                </span>
              ))}
            </div>
          )}
          {(attachments.length > 0 || attaching) && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {attachments.map((a) => (
                <span
                  key={a.id}
                  className="inline-flex max-w-[220px] items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 shadow-soft"
                  title={`${a.name} · ${a.char_count.toLocaleString("es-CO")} caracteres`}
                >
                  <FileText className="h-3.5 w-3.5 shrink-0 text-brand-600" />
                  <span className="truncate">{a.name}</span>
                  <button
                    type="button"
                    onClick={() => removeAttachment.mutate(a.id)}
                    className="shrink-0 text-slate-400 transition hover:text-red-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              {attaching && (
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-400">
                  Adjuntando…
                </span>
              )}
            </div>
          )}
          {attachError && <p className="mb-2 px-1 text-xs text-red-600">{attachError.message}</p>}

          <div className="rounded-2xl border border-slate-200 bg-white shadow-soft transition focus-within:border-brand-400 focus-within:shadow-[0_0_0_3px_rgba(16,185,129,0.12)]">
            <input
              ref={fileInputRef}
              type="file"
              accept={UPLOAD_ACCEPT}
              onChange={onFileChange}
              className="hidden"
            />
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Pregunta algo o pega una transcripción…"
              className="block max-h-[140px] w-full resize-none bg-transparent px-4 pb-1 pt-3 text-sm leading-relaxed text-slate-900 placeholder:text-slate-400 focus:outline-none"
            />
            <div className="flex items-center gap-1 px-2.5 pb-2.5 pt-1">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={attaching}
                title="Adjuntar un archivo (PDF, Word, transcripción…)"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40"
              >
                <Paperclip className="h-[18px] w-[18px]" />
              </button>
              <button
                ref={driveBtnRef}
                type="button"
                onClick={() => driveConnected && setShowDrive(true)}
                disabled={attaching || !driveConnected}
                title={driveConnected ? "Adjuntar desde Google Drive" : "Conecta tu Google para usar Drive"}
                className="flex h-8 items-center gap-1.5 rounded-lg px-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40"
              >
                <FolderOpen className="h-[18px] w-[18px]" />
                <span className="text-xs font-medium">Drive</span>
              </button>
              <div className="ml-auto flex items-center gap-2.5">
                <span className="hidden text-[11px] text-slate-400 sm:inline">↵ enviar</span>
                <button
                  type="button"
                  onClick={doSend}
                  disabled={!canSend}
                  title="Enviar"
                  className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm transition hover:bg-brand-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
                >
                  <ArrowUp className="h-[18px] w-[18px]" strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-slate-400">
            Las acciones (reuniones, correos, cambios) siempre piden tu confirmación.
          </p>
        </div>
      </div>

      {showDrive && (
        <DriveBrowser
          title="Adjuntar desde Drive"
          actionLabel="Enviar al agente"
          anchorRef={driveBtnRef}
          busy={attachDrive.isPending}
          pendingId={attachDrive.isPending ? (attachDrive.variables ?? null) : null}
          onClose={() => setShowDrive(false)}
          onPick={(entry) => attachDrive.mutate(entry.external_id)}
        />
      )}
    </div>
  );
}
