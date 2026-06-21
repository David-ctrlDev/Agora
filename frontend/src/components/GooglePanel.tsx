import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, Cloud, FileText, RefreshCw } from "lucide-react";

import { type GoogleDocument, googleStatus, listGoogleDocuments, syncGoogle } from "../api/google";
import { Badge, Button, Card, Spinner } from "./ui";

interface Props {
  projectId: number;
  canEdit: boolean;
}

function DocList({ docs }: { docs: GoogleDocument[] }) {
  if (docs.length === 0) return <li className="text-xs text-slate-400">—</li>;
  return (
    <>
      {docs.map((d) => (
        <li key={d.id} className="text-sm">
          <a
            href={d.web_url ?? "#"}
            target="_blank"
            rel="noreferrer"
            className="text-slate-800 transition hover:text-brand-600"
          >
            {d.title}
          </a>
          {d.occurred_at && (
            <span className="block text-xs text-slate-400">
              {new Date(d.occurred_at).toLocaleDateString("es-CO")}
            </span>
          )}
        </li>
      ))}
    </>
  );
}

export default function GooglePanel({ projectId, canEdit }: Props) {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ["google-status"], queryFn: googleStatus });
  const docsQuery = useQuery({
    queryKey: ["project", projectId, "google-docs"],
    queryFn: () => listGoogleDocuments(projectId),
  });

  const connected = statusQuery.data?.connected ?? false;
  const sync = useMutation({
    mutationFn: () => syncGoogle(projectId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["project", projectId, "google-docs"] }),
  });

  const docs = docsQuery.data ?? [];
  const drive = docs.filter((d) => d.source === "drive");
  const calendar = docs.filter((d) => d.source === "calendar");

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Cloud className="h-5 w-5 text-slate-700" />
          <h2 className="text-sm font-semibold text-slate-700">Google Workspace</h2>
        </div>
        <Badge tone={connected ? "success" : "neutral"}>
          {connected ? "Conectado" : "Sin conectar"}
        </Badge>
      </div>

      {!connected ? (
        <p className="text-sm text-slate-400">
          Conecta tu cuenta de Google desde la barra lateral para sincronizar Drive y Calendar de
          este proyecto.
        </p>
      ) : (
        <>
          {canEdit && (
            <div className="mb-4">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => sync.mutate()}
                disabled={sync.isPending}
              >
                <RefreshCw className="h-4 w-4" />
                {sync.isPending ? "Sincronizando…" : "Sincronizar Drive y Calendar"}
              </Button>
            </div>
          )}

          {docsQuery.isLoading ? (
            <Spinner label="Cargando…" />
          ) : docs.length === 0 ? (
            <p className="text-sm text-slate-400">
              Sin documentos. Sincroniza para traer archivos de Drive y eventos de Calendar.
            </p>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <FileText className="h-3.5 w-3.5" /> Drive
                </h3>
                <ul className="space-y-2">
                  <DocList docs={drive} />
                </ul>
              </div>
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <Calendar className="h-3.5 w-3.5" /> Calendar
                </h3>
                <ul className="space-y-2">
                  <DocList docs={calendar} />
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
