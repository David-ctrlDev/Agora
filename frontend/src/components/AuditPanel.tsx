import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";

import { getAudit } from "../api/audit";
import { Card, Spinner } from "./ui";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AuditPanel({ projectId }: { projectId: number }) {
  const query = useQuery({ queryKey: ["audit", projectId], queryFn: () => getAudit(projectId) });

  if (query.isLoading) {
    return (
      <Card className="p-5">
        <Spinner label="Cargando actividad…" />
      </Card>
    );
  }
  const entries = query.data ?? [];

  return (
    <Card className="p-5">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-700">
        <History className="h-4 w-4 text-slate-400" /> Actividad reciente
      </h2>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-400">Sin cambios registrados todavía.</p>
      ) : (
        <ul className="space-y-3">
          {entries.map((entry) => (
            <li key={entry.id} className="flex gap-3 text-sm">
              <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-300" />
              <div className="min-w-0 flex-1">
                <div className="text-slate-700">{entry.summary}</div>
                <div className="text-xs text-slate-400">
                  {entry.actor_name ?? "Sistema"} · {formatDate(entry.created_at)}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
