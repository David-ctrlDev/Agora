import AgentChat from "../components/AgentChat";
import { PageHeader } from "../components/ui";

export default function AgentPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Agente"
        description="Pregunta por el estado de tus proyectos o pídele acciones (crear proyectos, tareas, reuniones, correos). Las acciones requieren tu confirmación."
      />
      <div className="h-[62vh] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <AgentChat className="h-full" />
      </div>
    </div>
  );
}
