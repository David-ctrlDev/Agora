import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  Bell,
  Building2,
  FolderKanban,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { unreadCount } from "../api/notifications";
import { useLogout, useMe } from "../auth/useAuth";
import FloatingAgent from "./FloatingAgent";
import GoogleConnect from "./GoogleConnect";
import SessionManager from "./SessionManager";

const navItems = [
  { to: "/inicio", label: "Inicio", icon: LayoutDashboard },
  { to: "/areas", label: "Áreas", icon: Building2 },
  { to: "/proyectos", label: "Proyectos", icon: FolderKanban },
  { to: "/tareas", label: "Tareas", icon: ListChecks },
  { to: "/analitica", label: "Analítica", icon: BarChart3 },
  { to: "/agente", label: "Agente", icon: Sparkles },
  { to: "/notificaciones", label: "Notificaciones", icon: Bell },
  { to: "/seguridad", label: "Seguridad", icon: ShieldCheck },
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
  const [mobileOpen, setMobileOpen] = useState(false);

  // Cierra el menú móvil al navegar.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <SessionManager />
      {/* Backdrop del drawer (solo móvil) */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
          aria-hidden
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 transform flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient text-sm font-bold text-white shadow-sm">
            Á
          </div>
          <div className="leading-none">
            <div className="text-[15px] font-semibold tracking-tight text-slate-900">Ágora</div>
            <div className="mt-1 text-[11px] text-slate-400">Invesa</div>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="ml-auto rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 lg:hidden"
            aria-label="Cerrar menú"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Plataforma
        </div>
        <nav className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3">
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

          {(me.data?.is_superadmin ||
            me.data?.areas?.some((a) => a.area_role === "lead" || a.area_role === "admin")) && (
            <NavLink
              to={me.data?.is_superadmin ? "/admin" : "/area-admin"}
              className={({ isActive }) =>
                `group mt-1 flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <Settings className="h-[18px] w-[18px]" strokeWidth={2} />
              {me.data?.is_superadmin ? "Administración" : "Administración de área"}
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
                  {me.data.is_superadmin
                    ? "Super administrador"
                    : me.data.areas?.some((a) => a.area_role === "lead" || a.area_role === "admin")
                      ? "Administrador de área"
                      : "Miembro"}
                </div>
              </div>
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

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Barra superior (solo móvil) con la hamburguesa */}
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100"
            aria-label="Abrir menú"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-gradient text-xs font-bold text-white">
              Á
            </div>
            <span className="text-sm font-semibold text-slate-900">Ágora</span>
          </div>
          {unreadTotal > 0 && (
            <NavLink to="/notificaciones" className="relative ml-auto p-1.5 text-slate-500">
              <Bell className="h-5 w-5" />
              <span className="absolute right-0 top-0 h-2 w-2 rounded-full bg-brand-600" />
            </NavLink>
          )}
        </header>

        <main className="flex-1 overflow-auto">
          <div
            key={location.pathname}
            className="mx-auto max-w-6xl animate-fade-in px-4 py-6 sm:px-8 sm:py-8"
          >
            <Outlet />
          </div>
        </main>
      </div>

      <FloatingAgent />
    </div>
  );
}
