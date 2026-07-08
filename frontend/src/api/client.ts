async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // En multipart (FormData) dejamos que el navegador fije el Content-Type con su boundary.
  const isForm = options?.body instanceof FormData;
  const res = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(options?.headers ?? {}),
    },
  });

  if (!res.ok) {
    // Sesión expirada a mitad de uso: manda al login limpio. Se excluyen los
    // endpoints de auth (p. ej. /me al arrancar sin sesión, que RequireAuth ya
    // maneja) y la propia pantalla de login, para no marcar "expiró" a quien
    // nunca entró.
    if (
      res.status === 401 &&
      !path.startsWith("/api/auth/") &&
      !window.location.pathname.startsWith("/login")
    ) {
      window.location.assign("/login?expired=1");
    }
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // respuesta sin cuerpo JSON
    }
    const error = new Error(detail) as Error & { status?: number };
    error.status = res.status;
    throw error;
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};
