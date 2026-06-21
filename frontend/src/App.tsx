import { useQuery } from "@tanstack/react-query";

interface Health {
  status: string;
  app: string;
  env: string;
}

async function fetchHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error("API no disponible");
  return (await res.json()) as Health;
}

export default function App() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["health"], queryFn: fetchHealth });

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 text-slate-800">
      <h1 className="text-4xl font-bold">Ágora</h1>
      <p className="text-slate-500">Plataforma de gestión de proyectos · Invesa</p>
      <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm shadow-sm">
        {isLoading && <span>Comprobando API…</span>}
        {isError && <span className="text-red-600">API no disponible</span>}
        {data && (
          <span className="text-green-600">
            API: {data.status} · {data.app} · {data.env}
          </span>
        )}
      </div>
    </main>
  );
}
