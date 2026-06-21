import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { type FormEvent, useState } from "react";

import { type Area, createArea, listAreas } from "../api/areas";
import { useMe } from "../auth/useAuth";
import { Badge, Button, Card, Input, PageHeader, Spinner } from "../components/ui";

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
      <PageHeader
        title="Áreas"
        description={
          isAdmin
            ? "Departamentos de Invesa. Como administrador ves y gestionas todas."
            : "Áreas a las que perteneces."
        }
      />

      {isAdmin && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Nueva área</h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <Input
              label="Nombre"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="p. ej. Recursos Humanos"
              maxLength={120}
            />
            <Input
              label="Descripción (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descripción"
            />
            <Button type="submit" disabled={!name.trim() || create.isPending} className="shrink-0">
              <Plus className="h-4 w-4" />
              {create.isPending ? "Creando…" : "Crear área"}
            </Button>
          </form>
          {create.isError && (
            <p className="mt-3 text-sm text-red-600">{(create.error as Error).message}</p>
          )}
        </Card>
      )}

      <section>
        {areasQuery.isLoading && <Spinner label="Cargando áreas…" />}
        {areasQuery.isError && (
          <p className="text-sm text-red-600">No se pudieron cargar las áreas.</p>
        )}
        {areasQuery.data?.length === 0 && (
          <Card className="p-8 text-center text-sm text-slate-500">
            {isAdmin
              ? "Aún no hay áreas. Crea la primera arriba."
              : "No perteneces a ningún área todavía."}
          </Card>
        )}
        {areasQuery.data && areasQuery.data.length > 0 && (
          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Área</th>
                  <th className="px-5 py-3 font-medium">Slug</th>
                  <th className="px-5 py-3 font-medium">Estado</th>
                  <th className="px-5 py-3 font-medium">Creada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {areasQuery.data.map((area: Area) => (
                  <tr key={area.id} className="transition hover:bg-slate-50">
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
                      <Badge tone={area.is_active ? "success" : "neutral"}>
                        {area.is_active ? "Activa" : "Inactiva"}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {new Date(area.created_at).toLocaleDateString("es-CO")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </section>
    </div>
  );
}
