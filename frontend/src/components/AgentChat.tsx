import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  type AgentMessage,
  cancelAction,
  confirmAction,
  createConversation,
  listConversations,
  listMessages,
  sendMessage,
} from "../api/agent";
import { useAgentStore } from "../store/agentStore";
import { Button, Spinner } from "./ui";

const SUGGESTIONS = [
  "¿Cómo van mis proyectos?",
  "¿Qué tareas están vencidas?",
  "Crea el proyecto Innovación en IT",
  "Crea una reunión con ana@invesa.com mañana",
];

function MessageBubble({
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
  const isUser = message.role === "user";
  const pending = message.action?.status === "pending";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {pending && (
          <div className="mt-3 flex gap-2">
            <Button size="sm" onClick={onConfirm} disabled={busy}>
              Confirmar
            </Button>
            <Button size="sm" variant="secondary" onClick={onCancel} disabled={busy}>
              Cancelar
            </Button>
          </div>
        )}
        {message.action?.status === "executed" && (
          <p className="mt-1 text-xs text-slate-400">acción ejecutada ✓</p>
        )}
        {message.action?.status === "cancelled" && (
          <p className="mt-1 text-xs text-slate-400">acción cancelada</p>
        )}
      </div>
    </div>
  );
}

export default function AgentChat({ className = "" }: { className?: string }) {
  const queryClient = useQueryClient();
  const conversationId = useAgentStore((s) => s.activeConversationId);
  const setConversationId = useAgentStore((s) => s.setActiveConversationId);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const conversationsQuery = useQuery({ queryKey: ["agent-convs"], queryFn: listConversations });

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

  const send = useMutation({
    mutationFn: async (content: string) => {
      let cid = conversationId;
      if (cid === null) {
        const conversation = await createConversation();
        cid = conversation.id;
        setConversationId(cid);
        void queryClient.invalidateQueries({ queryKey: ["agent-convs"] });
      }
      return sendMessage(cid, content);
    },
    onSuccess: invalidate,
  });
  const confirm = useMutation({ mutationFn: confirmAction, onSuccess: invalidate });
  const cancel = useMutation({ mutationFn: cancelAction, onSuccess: invalidate });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messagesQuery.data]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    send.mutate(text);
  };

  const messages = messagesQuery.data ?? [];

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {conversationId !== null && messagesQuery.isLoading && <Spinner label="Cargando…" />}
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">Pregúntame o pídeme una acción:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send.mutate(s)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-brand-300 hover:bg-brand-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onConfirm={() => m.action && confirm.mutate(m.action.id)}
            onCancel={() => m.action && cancel.mutate(m.action.id)}
            busy={confirm.isPending || cancel.isPending}
          />
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="flex items-center gap-2 border-t border-slate-200 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu mensaje…"
          className="h-10 flex-1 rounded-lg border border-slate-300 px-3 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
        />
        <Button type="submit" disabled={!input.trim() || send.isPending}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
