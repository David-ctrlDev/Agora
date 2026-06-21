import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CircleDot,
  GitCommitHorizontal,
  GitPullRequest,
  GitBranch,
  type LucideIcon,
  Plus,
  RefreshCw,
  Tag,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { type GitHubEvent, linkRepo, listActivity, listRepos, syncRepo, unlinkRepo } from "../api/github";
import { Button, Card, Input, Spinner } from "./ui";

const EVENT_ICON: Record<string, LucideIcon> = {
  push: GitCommitHorizontal,
  pull_request: GitPullRequest,
  release: Tag,
  issues: CircleDot,
};

const EVENT_LABEL: Record<string, string> = {
  push: "commit",
  pull_request: "pull request",
  release: "release",
  issues: "issue",
};

interface Props {
  projectId: number;
  canEdit: boolean;
}

export default function GitHubPanel({ projectId, canEdit }: Props) {
  const queryClient = useQueryClient();
  const reposQuery = useQuery({
    queryKey: ["project", projectId, "repos"],
    queryFn: () => listRepos(projectId),
  });
  const activityQuery = useQuery({
    queryKey: ["project", projectId, "gh-activity"],
    queryFn: () => listActivity(projectId),
  });
  const [fullName, setFullName] = useState("");

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["project", projectId, "repos"] });
    void queryClient.invalidateQueries({ queryKey: ["project", projectId, "gh-activity"] });
  };
  const link = useMutation({
    mutationFn: () => linkRepo(projectId, fullName.trim()),
    onSuccess: () => {
      invalidate();
      setFullName("");
    },
  });
  const unlink = useMutation({ mutationFn: (id: number) => unlinkRepo(id), onSuccess: invalidate });
  const sync = useMutation({ mutationFn: (id: number) => syncRepo(id), onSuccess: invalidate });

  const repos = reposQuery.data ?? [];
  const activity = activityQuery.data ?? [];

  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center gap-2">
        <GitBranch className="h-5 w-5 text-slate-700" />
        <h2 className="text-sm font-semibold text-slate-700">Actividad de GitHub</h2>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {repos.map((r) => (
          <span
            key={r.id}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-1 text-xs"
          >
            <span className="font-medium text-slate-700">{r.full_name}</span>
            {canEdit && (
              <>
                <button
                  type="button"
                  onClick={() => sync.mutate(r.id)}
                  title="Sincronizar"
                  className="text-slate-400 transition hover:text-brand-600"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => unlink.mutate(r.id)}
                  title="Desvincular"
                  className="text-slate-400 transition hover:text-red-600"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </span>
        ))}
        {repos.length === 0 && (
          <span className="text-xs text-slate-400">Sin repositorios vinculados.</span>
        )}
      </div>

      {canEdit && (
        <div className="mb-4 flex items-end gap-2">
          <Input
            label="Vincular repositorio"
            placeholder="owner/repo"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <Button
            onClick={() => {
              if (fullName.trim()) link.mutate();
            }}
            disabled={!fullName.trim() || link.isPending}
          >
            <Plus className="h-4 w-4" /> Vincular
          </Button>
        </div>
      )}
      {link.isError && <p className="mb-3 text-sm text-red-600">{(link.error as Error).message}</p>}

      {activityQuery.isLoading ? (
        <Spinner label="Cargando actividad…" />
      ) : activity.length === 0 ? (
        <p className="text-sm text-slate-400">
          Sin actividad. Vincula un repositorio para ver sus commits, PRs, releases e issues.
        </p>
      ) : (
        <ul className="space-y-2.5">
          {activity.slice(0, 20).map((e: GitHubEvent) => {
            const Icon = EVENT_ICON[e.event_type] ?? GitCommitHorizontal;
            return (
              <li key={e.id} className="flex items-start gap-3 text-sm">
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                <div className="min-w-0 flex-1">
                  <a
                    href={e.html_url ?? "#"}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-800 transition hover:text-brand-600"
                  >
                    {e.title}
                  </a>
                  <div className="text-xs text-slate-400">
                    {EVENT_LABEL[e.event_type] ?? e.event_type}
                    {e.author ? ` · ${e.author}` : ""} ·{" "}
                    {new Date(e.occurred_at).toLocaleDateString("es-CO")}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
