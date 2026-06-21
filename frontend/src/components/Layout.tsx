import { useQuery } from "@tanstack/react-query";
import { BarChart3, Bell, Building2, FolderKanban, ListChecks, LogOut, Sparkles } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { unreadCount } from "../api/notifications";
import { useLogout, useMe } from "../auth/useAuth";
import FloatingAgent from "./FloatingAgent";
import GoogleConnect from "./GoogleConnect";

const navItems = [
  { to: "/areas", label: "Áreas", icon: Building2 },
  { to: "/proyectos", label: "Proyectos", icon: FolderKanban },
  { to: "/tareas", label: "Tareas", icon: ListChecks },
  { to: "/analitica", label: "Analítica", icon: BarChart3 },
  { to: "/agente", label: "Agente", icon: Sparkles },
  { to: "/notificaciones", label: "Notificaciones", icon: Bell },
];

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function ApiStatus() {
  const { isSuccess, isError } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("API sin conexión");
      return res.json();
    },
    refetchInterval: 30000,
  });
  const ok = isSuccess && !isError;
  return (
    <div className="flex items-center gap-2 text-xs text-slate-400">
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-red-400"}`} />
      API {ok ? "conectada" : "sin conexión"}
    </div>
  );
}

export default function Layout() {
  const me = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const unread = useQuery({
    queryKey: ["notif-count"],
    queryFn: unreadCount,
    refetchInterval: 30000,
  });
  const unreadTotal = unread.data?.count ?? 0;

  const handleLogout = () => {
    logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) });
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-64 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 px-6 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            Á
          </div>
          <span className="text-lg font-semibold tracking-tight text-slate-900">Ágora</span>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <Icon className="h-5 w-5" strokeWidth={2} />
              {label}
              {to === "/notificaciones" && unreadTotal > 0 && (
                <span className="ml-auto rounded-full bg-brand-600 px-1.5 py-0.5 text-xs font-semibold text-white">
                  {unreadTotal}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-200 p-3">
          {me.data && (
            <div className="flex items-center gap-3 rounded-lg px-2 py-2">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
                {getInitials(me.data.name)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-slate-900">{me.data.name}</div>
                <div className="text-xs text-slate-500">
                  {me.data.role === "admin" ? "Administrador" : "Miembro"}
                </div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                title="Salir"
                className="rounded-md p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className="px-1">
            <GoogleConnect />
          </div>
          <div className="px-2 pt-2">
            <ApiStatus />
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <Outlet />
        </div>
      </main>

      <FloatingAgent />
    </div>
  );
}
