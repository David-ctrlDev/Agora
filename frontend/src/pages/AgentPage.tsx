import AgentChat from "../components/AgentChat";
import AgoraMark from "../components/AgoraMark";

export default function AgentPage() {
  return (
    <div className="flex h-full flex-col space-y-5">
      <div className="flex items-start gap-3">
        <AgoraMark className="h-11 w-11" />
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Asistente Ágora</h1>
          <p className="mt-0.5 max-w-2xl text-sm text-slate-500">
            Pregunta por el estado de tus proyectos, riesgos y entregas, o pídele acciones —
            crear proyectos, tareas, reuniones o correos. Las acciones requieren tu confirmación.
          </p>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
        <AgentChat className="h-full" />
      </div>
    </div>
  );
}
