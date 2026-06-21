import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { type DevUser, devLogin, listDevUsers } from "../api/auth";
import { useMe } from "../auth/useAuth";

export default function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const me = useMe();
  const devUsers = useQuery({ queryKey: ["dev-users"], queryFn: listDevUsers, retry: false });

  const login = useMutation({
    mutationFn: (userId: number) => devLogin(userId),
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      navigate("/areas", { replace: true });
    },
  });

  useEffect(() => {
    if (me.data) navigate("/areas", { replace: true });
  }, [me.data, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">
        <h1 className="text-3xl font-bold text-slate-900">Ágora</h1>
        <p className="mt-1 text-sm text-slate-500">
          Plataforma de gestión de proyectos · Invesa
        </p>

        <div className="mt-6 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Modo desarrollo — entra como un usuario de prueba. El login con Google llegará en la Fase 3.
        </div>

        <div className="mt-6 space-y-2">
          {devUsers.isLoading && <p className="text-sm text-slate-500">Cargando usuarios…</p>}
          {devUsers.isError && (
            <p className="text-sm text-red-600">No se pudo cargar la lista de usuarios.</p>
          )}
          {devUsers.data?.map((user: DevUser) => (
            <button
              key={user.id}
              type="button"
              onClick={() => login.mutate(user.id)}
              disabled={login.isPending}
              className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-200 px-4 py-3 text-left transition hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50"
            >
              <span className="min-w-0">
                <span className="block font-medium text-slate-900">{user.name}</span>
                <span className="block truncate text-xs text-slate-500">{user.email}</span>
              </span>
              <span className="flex shrink-0 flex-col items-end gap-1">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    user.role === "admin"
                      ? "bg-indigo-100 text-indigo-700"
                      : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {user.role === "admin" ? "Admin" : "Miembro"}
                </span>
                <span className="text-xs text-slate-400">{user.areas.join(", ")}</span>
              </span>
            </button>
          ))}
        </div>

        {login.isError && (
          <p className="mt-3 text-sm text-red-600">{(login.error as Error).message}</p>
        )}
      </div>
    </div>
  );
}
