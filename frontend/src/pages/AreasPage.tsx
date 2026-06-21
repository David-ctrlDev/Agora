import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { type Area, createArea, listAreas } from "../api/areas";
import { useMe } from "../auth/useAuth";

export default function AreasPage() {
  const queryClient = useQueryClient();
  const me = useMe();
  const isAdmin = me.data?.role === "admin";

  const areasQuery = useQuery({ queryKey: ["areas"], queryFn: listAreas });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const create = useMutation({
    mutationFn: createArea,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["areas"] });
      setName("");
      setDescription("");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate({ name: trimmed, description: description.trim() || null });
  };

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Áreas</h1>
        <p className="text-sm text-slate-500">
          {isAdmin
            ? "Departamentos de Invesa. Como administrador ves y gestionas todas."
            : "Áreas a las que perteneces."}
        </p>
      </header>

      {isAdmin && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Nueva área
          </h2>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <label className="flex-1">
              <span className="mb-1 block text-sm font-medium text-slate-700">Nombre</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="p. ej. Recursos Humanos"
                maxLength={120}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              />
            </label>
            <label className="flex-1">
              <span className="mb-1 block text-sm font-medium text-slate-700">
                Descripción <span className="font-normal text-slate-400">(opcional)</span>
              </span>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Breve descripción"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              />
            </label>
            <button
              type="submit"
              disabled={!name.trim() || create.isPending}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {create.isPending ? "Creando…" : "Crear área"}
            </button>
          </div>
          {create.isError && (
            <p className="mt-3 text-sm text-red-600">{(create.error as Error).message}</p>
          )}
        </form>
      )}

      <section>
        {areasQuery.isLoading && <p className="text-sm text-slate-500">Cargando áreas…</p>}
        {areasQuery.isError && (
          <p className="text-sm text-red-600">No se pudieron cargar las áreas.</p>
        )}
        {areasQuery.data?.length === 0 && (
          <p className="text-sm text-slate-500">
            {isAdmin ? "Aún no hay áreas. Crea la primera arriba." : "No perteneces a ningún área todavía."}
          </p>
        )}
        {areasQuery.data && areasQuery.data.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Área</th>
                  <th className="px-5 py-3 font-medium">Slug</th>
                  <th className="px-5 py-3 font-medium">Estado</th>
                  <th className="px-5 py-3 font-medium">Creada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {areasQuery.data.map((area: Area) => (
                  <tr key={area.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-900">{area.name}</div>
                      {area.description && (
                        <div className="text-xs text-slate-500">{area.description}</div>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                        {area.slug}
                      </code>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          area.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {area.is_active ? "Activa" : "Inactiva"}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {new Date(area.created_at).toLocaleDateString("es-CO")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
