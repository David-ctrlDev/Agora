import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  Bell,
  Building2,
  FolderKanban,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { unreadCount } from "../api/notifications";
import { useLogout, useMe } from "../auth/useAuth";
import FloatingAgent from "./FloatingAgent";
import GoogleConnect from "./GoogleConnect";

const navItems = [
  { to: "/inicio", label: "Inicio", icon: LayoutDashboard },
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
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"}`} />
      API {ok ? "conectada" : "sin conexión"}
    </div>
  );
}

export default function Layout() {
  const me = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
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
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient text-sm font-bold text-white shadow-sm">
            Á
          </div>
          <div className="leading-none">
            <div className="text-[15px] font-semibold tracking-tight text-slate-900">Ágora</div>
            <div className="mt-1 text-[11px] text-slate-400">Invesa</div>
          </div>
        </div>

        <div className="px-5 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Plataforma
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <Icon className="h-[18px] w-[18px]" strokeWidth={2} />
              {label}
              {to === "/notificaciones" && unreadTotal > 0 && (
                <span className="ml-auto rounded-full bg-brand-100 px-1.5 py-0.5 text-[11px] font-semibold text-brand-700">
                  {unreadTotal}
                </span>
              )}
            </NavLink>
          ))}

          {me.data?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `group mt-1 flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <Settings className="h-[18px] w-[18px]" strokeWidth={2} />
              Administración
            </NavLink>
          )}
        </nav>

        <div className="space-y-2 border-t border-slate-200 p-3">
          {me.data && (
            <div className="flex items-center gap-3 rounded-xl px-2 py-1.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-sm font-semibold text-white">
                {getInitials(me.data.name)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-slate-900">{me.data.name}</div>
                <div className="text-xs text-slate-500">
                  {me.data.role === "admin" ? "Administrador" : "Miembro"}
                </div>
              </div>
              <Link
                to="/seguridad"
                title="Seguridad"
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <ShieldCheck className="h-4 w-4" />
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                title="Salir"
                className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
          <GoogleConnect />
          <div className="px-2 pt-1">
            <ApiStatus />
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div
          key={location.pathname}
          className="mx-auto max-w-6xl animate-fade-in px-6 py-8 sm:px-8"
        >
          <Outlet />
        </div>
      </main>

      <FloatingAgent />
    </div>
  );
}
