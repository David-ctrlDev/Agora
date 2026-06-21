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
        title="Abrir asistente"
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-lg ring-4 ring-brand-500/15 transition hover:scale-105 hover:shadow-xl"
      >
        <Sparkles className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-slate-200 bg-slate-50 shadow-2xl">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Asistente Ágora</div>
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Con tecnología Gemini
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={close}
          title="Cerrar"
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-5 w-5" />
        </button>
      </header>
      <AgentChat className="flex-1" />
    </div>
  );
}
