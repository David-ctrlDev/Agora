import { Sparkles, X } from "lucide-react";

import { useAgentStore } from "../store/agentStore";
import AgentChat from "./AgentChat";

export default function FloatingAgent() {
  const isOpen = useAgentStore((s) => s.isOpen);
  const open = useAgentStore((s) => s.open);
  const close = useAgentStore((s) => s.close);

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={open}
        title="Abrir agente"
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg transition hover:bg-brand-700"
      >
        <Sparkles className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-brand-600" />
          <span className="font-semibold text-slate-900">Agente</span>
        </div>
        <button
          type="button"
          onClick={close}
          title="Cerrar"
          className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <AgentChat className="min-h-0 flex-1" />
    </div>
  );
}
