import { X } from "lucide-react";

import { useAgentStore } from "../store/agentStore";
import AgentChat from "./AgentChat";
import AgoraMark from "./AgoraMark";

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
        className="group fixed bottom-6 right-6 z-40 flex items-center gap-2.5 rounded-2xl bg-white/90 py-2 pl-2 pr-4 shadow-pop ring-1 ring-slate-200/70 backdrop-blur transition hover:-translate-y-0.5 hover:shadow-xl"
      >
        <span className="relative">
          <AgoraMark className="h-9 w-9" />
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white" />
        </span>
        <span className="text-left leading-tight">
          <span className="block text-sm font-semibold text-slate-900">Ágora</span>
          <span className="block text-[11px] text-slate-400">Preguntar al asistente</span>
        </span>
      </button>
    );
  }

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3">
        <div className="flex items-center gap-3">
          <AgoraMark className="h-9 w-9" />
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight text-slate-900">Asistente Ágora</div>
            <div className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
              <span className="h-1 w-1 rounded-full bg-brand-500" /> Gemini
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
