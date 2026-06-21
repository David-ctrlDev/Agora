import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/areas", label: "Áreas", icon: "▦" },
  { to: "/proyectos", label: "Proyectos", icon: "▤" },
  { to: "/tareas", label: "Tareas", icon: "☑" },
];

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
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-green-400" : "bg-red-400"}`} />
      API {ok ? "conectada" : "sin conexión"}
    </div>
  );
}

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-800">
      <aside className="flex w-60 flex-col bg-slate-900 text-slate-100">
        <div className="px-6 py-5 text-2xl font-bold tracking-tight">Ágora</div>
        <nav className="flex-1 space-y-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              <span className="w-4 text-center">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 px-6 py-4">
          <ApiStatus />
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-5xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
