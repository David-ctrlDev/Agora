import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  ChevronDown,
  FileText,
  FolderOpen,
  MessagesSquare,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { type ChangeEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import {
  type AgentMessage,
  type Attachment,
  attachFromDrive,
  cancelAction,
  confirmAction,
  createConversation,
  deleteAttachment,
  deleteConversation,
  listConversations,
  listMessages,
  sendMessage,
  uploadAttachment,
} from "../api/agent";
import { googleStatus } from "../api/google";
import { useAgentStore } from "../store/agentStore";
import DriveBrowser from "./DriveBrowser";
import Markdown from "./Markdown";
import { Spinner } from "./ui";

const UPLOAD_ACCEPT = ".pdf,.doc,.docx,.txt,.md,.csv,.vtt,.srt,.log";

const SUGGESTIONS = [
  "¿Cómo van mis proyectos?",
  "¿Qué tareas tengo pendientes?",
  "¿Qué tareas están vencidas?",
  "Agenda una reunión con ana@invesa.com mañana",
];

function AssistantAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
      <Sparkles className="h-4 w-4" />
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
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
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  const status = message.action?.status;
  return (
    <div className="flex gap-2.5">
      <AssistantAvatar />
      <div className="max-w-[85%] space-y-2">
        <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm">
          <Markdown>{message.content}</Markdown>
        </div>
        {status === "pending" && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onConfirm}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" /> Confirmar
            </button>
            <button
              type="button"
              onClick={onCancel}
              disabled={busy}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
            >
              Cancelar
            </button>
          </div>
        )}
        {status === "executed" && <p className="px-1 text-xs text-emerald-600">✓ Acción ejecutada</p>}
        {status === "cancelled" && <p className="px-1 text-xs text-slate-400">Acción cancelada</p>}
      </div>
    </div>
  );
}

export default function AgentChat({ className = "" }: { className?: string }) {
  const queryClient = useQueryClient();
  const conversationId = useAgentStore((s) => s.activeConversationId);
  const setConversationId = useAgentStore((s) => s.setActiveConversationId);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<{ text: string; files: string[] } | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [showDrive, setShowDrive] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const conversationsQuery = useQuery({ queryKey: ["agent-convs"], queryFn: listConversations });
  const googleQuery = useQuery({ queryKey: ["google-status"], queryFn: googleStatus });
  const driveConnected = googleQuery.data?.connected ?? false;

  useEffect(() => {
    if (conversationId === null && conversationsQuery.data && conversationsQuery.data.length > 0) {
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
    onSuccess: (att) => setAttachments((a) => [...a, att]),
  });

  const attachDrive = useMutation({
    mutationFn: async (fileId: string) => {
      const cid = await ensureConversation();
      return attachFromDrive(cid, fileId);
    },
    onSuccess: (att) => {
      setAttachments((a) => [...a, att]);
      setShowDrive(false);
    },
  });

  const removeAttachment = useMutation({
    mutationFn: deleteAttachment,
    onSuccess: (_data, id) => setAttachments((a) => a.filter((x) => x.id !== id)),
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
    setConversationId(null);
    setHistoryOpen(false);
    setInput("");
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messagesQuery.data, send.isPending, pending]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
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

  return (
    <div className={`flex min-h-0 flex-col ${className}`}>
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
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
              <div className="absolute left-0 top-full z-20 mt-1 max-h-72 w-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1 shadow-lg">
                {conversations.length === 0 ? (
                  <p className="px-3 py-2 text-sm text-slate-400">Aún no hay conversaciones.</p>
                ) : (
                  conversations.map((c) => (
                    <div
                      key={c.id}
                      className={`group flex items-center gap-1 rounded-lg ${
                        c.id === conversationId ? "bg-brand-50" : "hover:bg-slate-50"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setConversationId(c.id);
                          setHistoryOpen(false);
                        }}
                        className="min-w-0 flex-1 px-2 py-1.5 text-left"
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
                        className="mr-1 rounded p-1 text-slate-300 opacity-0 transition hover:text-red-600 group-hover:opacity-100"
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
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
        >
          <Plus className="h-4 w-4" /> Nuevo
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {loadingHistory ? (
          <Spinner label="Cargando…" />
        ) : showEmpty ? (
          <div className="flex h-full flex-col items-center justify-center px-2 text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
              <Sparkles className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-800">¿En qué te ayudo hoy?</h3>
            <p className="mt-1 max-w-xs text-sm text-slate-500">
              Pregúntame por tus proyectos y tareas, o pídeme una acción.
            </p>
            <div className="mt-5 grid w-full max-w-sm gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => submit(s)}
                  className="rounded-xl border border-slate-200 px-3 py-2 text-left text-sm text-slate-600 transition hover:border-brand-300 hover:bg-brand-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
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
              <div className="flex justify-end">
                <div className="max-w-[85%] space-y-1">
                  <div className="whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
                    {pending.text}
                  </div>
                  {pending.files.length > 0 && (
                    <div className="flex flex-wrap justify-end gap-1">
                      {pending.files.map((f) => (
                        <span
                          key={f}
                          className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-1.5 py-0.5 text-[11px] text-brand-700"
                        >
                          <FileText className="h-3 w-3" /> {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            {send.isPending && (
              <div className="flex gap-2.5">
                <AssistantAvatar />
                <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white shadow-sm">
                  <TypingDots />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 p-3">
        {(attachments.length > 0 || attaching) && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {attachments.map((a) => (
              <span
                key={a.id}
                className="inline-flex max-w-[220px] items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600"
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
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-400">
                Adjuntando…
              </span>
            )}
          </div>
        )}
        {attachError && <p className="mb-2 px-1 text-xs text-red-600">{attachError.message}</p>}
        <div className="flex items-end gap-1 rounded-2xl border border-slate-300 bg-white px-2 py-2 transition focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20">
          <input
            ref={fileInputRef}
            type="file"
            accept={UPLOAD_ACCEPT}
            onChange={onFileChange}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={attaching}
            title="Adjuntar un archivo (PDF, Word, transcripción…)"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40"
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => driveConnected && setShowDrive(true)}
            disabled={attaching || !driveConnected}
            title={driveConnected ? "Adjuntar desde Google Drive" : "Conecta tu Google para usar Drive"}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40"
          >
            <FolderOpen className="h-4 w-4" />
          </button>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Escribe tu mensaje…"
            className="max-h-[120px] flex-1 resize-none bg-transparent px-1 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
          <button
            type="button"
            onClick={doSend}
            disabled={(!input.trim() && attachments.length === 0) || send.isPending || attaching}
            title="Enviar"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition hover:bg-brand-700 disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1.5 px-1 text-[11px] text-slate-400">
          Adjunta un archivo o uno de Drive y pídeme, p. ej., un cronograma de tareas.
        </p>
      </div>
      {showDrive && (
        <DriveBrowser
          title="Adjuntar desde Drive"
          actionLabel="Enviar al agente"
          busy={attachDrive.isPending}
          pendingId={attachDrive.isPending ? (attachDrive.variables ?? null) : null}
          onClose={() => setShowDrive(false)}
          onPick={(entry) => attachDrive.mutate(entry.external_id)}
        />
      )}
    </div>
  );
}
