import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { type DevUser, devLogin, listDevUsers } from "../api/auth";
import { useMe } from "../auth/useAuth";
import { Badge, Card, Spinner } from "../components/ui";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-lg font-bold text-white">
            Á
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">Ágora</h1>
            <p className="text-sm text-slate-500">Gestión de proyectos · Invesa</p>
          </div>
        </div>

        <div className="mb-5 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Modo desarrollo — entra como un usuario de prueba. El acceso con Google llegará en la
            Fase 3.
          </span>
        </div>

        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Entrar como
        </p>

        <div className="space-y-2">
          {devUsers.isLoading && <Spinner label="Cargando usuarios…" />}
          {devUsers.isError && (
            <p className="text-sm text-red-600">No se pudo cargar la lista de usuarios.</p>
          )}
          {devUsers.data?.map((user: DevUser) => (
            <button
              key={user.id}
              type="button"
              onClick={() => login.mutate(user.id)}
              disabled={login.isPending}
              className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left transition hover:border-brand-300 hover:bg-brand-50/40 disabled:opacity-50"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">
                {getInitials(user.name)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium text-slate-900">{user.name}</span>
                  <Badge tone={user.role === "admin" ? "brand" : "neutral"}>
                    {user.role === "admin" ? "Admin" : "Miembro"}
                  </Badge>
                </div>
                <div className="truncate text-xs text-slate-500">{user.email}</div>
                <div className="mt-0.5 truncate text-xs text-slate-400">
                  {user.areas.join(" · ")}
                </div>
              </div>
            </button>
          ))}
        </div>

        {login.isError && (
          <p className="mt-3 text-sm text-red-600">{(login.error as Error).message}</p>
        )}
      </Card>
    </div>
  );
}
