import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, RefreshCw } from "lucide-react";

import {
  type Notification,
  listNotifications,
  markAllRead,
  markRead,
  runDetection,
} from "../api/notifications";
import { useMe } from "../auth/useAuth";
import { Badge, Button, Card, PageHeader, Spinner } from "../components/ui";

type Tone = "neutral" | "warning" | "danger";
const SEVERITY_TONE: Record<string, Tone> = {
  info: "neutral",
  warning: "warning",
  danger: "danger",
};

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const me = useMe();
  const notificationsQuery = useQuery({ queryKey: ["notifications"], queryFn: listNotifications });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    void queryClient.invalidateQueries({ queryKey: ["notif-count"] });
  };
  const run = useMutation({ mutationFn: runDetection, onSuccess: invalidate });
  const allRead = useMutation({ mutationFn: markAllRead, onSuccess: invalidate });
  const read = useMutation({ mutationFn: (id: number) => markRead(id), onSuccess: invalidate });

  const items = notificationsQuery.data ?? [];
  const isAdmin = me.data?.role === "admin";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notificaciones"
        description="Alertas de riesgo de tus áreas: tareas vencidas o bloqueadas y entregas en riesgo."
        actions={
          <div className="flex gap-2">
            {isAdmin && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => run.mutate()}
                disabled={run.isPending}
              >
                <RefreshCw className="h-4 w-4" />
                {run.isPending ? "Analizando…" : "Ejecutar detección"}
              </Button>
            )}
            <Button size="sm" variant="secondary" onClick={() => allRead.mutate()}>
              <CheckCheck className="h-4 w-4" /> Marcar todas
            </Button>
          </div>
        }
      />

      {notificationsQuery.isLoading && <Spinner label="Cargando…" />}
      {!notificationsQuery.isLoading && items.length === 0 && (
        <Card className="p-8 text-center text-sm text-slate-500">Sin notificaciones. 🎉</Card>
      )}
      {items.length > 0 && (
        <Card className="divide-y divide-slate-100">
          {items.map((n: Notification) => (
            <div
              key={n.id}
              className={`flex items-start justify-between gap-3 p-4 ${
                n.status === "unread" ? "bg-brand-50/40" : ""
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-900">{n.title}</span>
                  <Badge tone={SEVERITY_TONE[n.severity] ?? "neutral"}>{n.severity}</Badge>
                </div>
                <p className="text-sm text-slate-500">{n.body}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {new Date(n.created_at).toLocaleString("es-CO")}
                </p>
              </div>
              {n.status === "unread" && (
                <button
                  type="button"
                  onClick={() => read.mutate(n.id)}
                  className="shrink-0 text-xs text-brand-600 hover:underline"
                >
                  marcar leída
                </button>
              )}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
