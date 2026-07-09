import { api } from "./client";

export interface CommitInfo {
  hash: string;
  short: string;
  author: string;
  date: string;
  message: string;
  files: string[];
}

export interface BranchInfo {
  name: string;
  is_default: boolean;
  last: { short: string; author: string; date: string; message: string } | null;
  ahead: number;
}

export interface CodeStatus {
  initialized: boolean;
  default_branch: string;
  branches: BranchInfo[];
}

export interface ChangedFile {
  status: string;
  path: string;
}

export interface GitignoreCategory {
  id: string;
  title: string;
  description: string;
  patterns: string[];
  recommended: boolean;
}

export interface GitignoreState {
  content: string;
  active: string[];
  extra: string;
  categories: GitignoreCategory[];
}

export interface DiffResult {
  files: ChangedFile[];
  diffs: Record<string, string>;
  binary: string[];
}

const base = (projectId: number) => `/api/projects/${projectId}/code`;

export const getCodeStatus = (projectId: number) => api.get<CodeStatus>(`${base(projectId)}/status`);
export const listCommits = (projectId: number, branch: string) =>
  api.get<CommitInfo[]>(`${base(projectId)}/commits?branch=${encodeURIComponent(branch)}&limit=30`);
export const zipUrl = (projectId: number, ref: string) =>
  `${base(projectId)}/zip?ref=${encodeURIComponent(ref)}`;

export const uploadCode = (
  projectId: number,
  files: { file: File; path: string }[],
  message: string,
  branch: string,
) => {
  const form = new FormData();
  for (const f of files) form.append("files", f.file, f.path);
  form.append("message", message);
  form.append("branch", branch);
  return api.upload<CommitInfo>(`${base(projectId)}/upload`, form);
};

export const restoreCommit = (projectId: number, hash: string, branch: string) =>
  api.post<CommitInfo>(`${base(projectId)}/restore`, { hash, branch });

export const getGitignore = (projectId: number) => api.get<GitignoreState>(`${base(projectId)}/gitignore`);
export const setGitignore = (projectId: number, categories: string[], extra: string) =>
  api.put<CommitInfo>(`${base(projectId)}/gitignore`, { categories, extra });

export const createBranch = (projectId: number, name: string) =>
  api.post<{ name: string }>(`${base(projectId)}/branches`, { name });
export const deleteBranch = (projectId: number, branch: string) =>
  api.del<void>(`${base(projectId)}/branches/${encodeURIComponent(branch)}`);
export const branchDiff = (projectId: number, branch: string) =>
  api.get<DiffResult>(`${base(projectId)}/branches/${encodeURIComponent(branch)}/diff`);

/** Publica un borrador. Devuelve el commit, o la lista de conflictos si los hay. */
export async function mergeBranch(
  projectId: number,
  branch: string,
  resolutions?: Record<string, "draft" | "main">,
): Promise<{ ok: true; commit: CommitInfo } | { ok: false; conflicts: string[] }> {
  const res = await fetch(`${base(projectId)}/merge`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ branch, resolutions }),
  });
  if (res.status === 409) {
    const body = (await res.json()) as { detail?: { conflicts?: string[] } };
    return { ok: false, conflicts: body.detail?.conflicts ?? [] };
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* sin cuerpo */
    }
    throw new Error(detail);
  }
  return { ok: true, commit: (await res.json()) as CommitInfo };
}
