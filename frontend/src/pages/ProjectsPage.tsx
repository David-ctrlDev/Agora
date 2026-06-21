import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { listAreas } from "../api/areas";
import {
  PROJECT_STATUS,
  type Project,
  type ProjectStatus,
  createProject,
  listProjects,
} from "../api/projects";
import { Badge, Button, Card, Input, PageHeader, Select, Spinner } from "../components/ui";

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const areasQuery = useQuery({ queryKey: ["areas"], queryFn: listAreas });

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [areaId, setAreaId] = useState<number | "">("");
  const [status, setStatus] = useState<ProjectStatus>("planned");
  const [dueDate, setDueDate] = useState("");
  const [description, setDescription] = useState("");

  const create = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setName("");
      setAreaId("");
      setStatus("planned");
      setDueDate("");
      setDescription("");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || areaId === "") return;
    create.mutate({
      name: name.trim(),
      area_id: Number(areaId),
      status,
      due_date: dueDate || null,
      description: description.trim() || null,
    });
  };

  const areas = areasQuery.data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Proyectos"
        description="Proyectos de tus áreas."
        actions={
          areas.length > 0 ? (
            <Button
              onClick={() => setShowForm((v) => !v)}
              variant={showForm ? "secondary" : "primary"}
            >
              <Plus className="h-4 w-4" /> Nuevo proyecto
            </Button>
          ) : null
        }
      />

      {showForm && (
        <Card className="p-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nombre del proyecto"
                maxLength={200}
              />
              <Select
                label="Área"
                value={areaId}
                onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Selecciona un área</option>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
              <Select
                label="Estado"
                value={status}
                onChange={(e) => setStatus(e.target.value as ProjectStatus)}
              >
                {Object.entries(PROJECT_STATUS).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value.label}
                  </option>
                ))}
              </Select>
              <Input
                label="Fecha de entrega"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            <Input
              label="Descripción (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descripción"
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={!name.trim() || areaId === "" || create.isPending}>
                {create.isPending ? "Creando…" : "Crear proyecto"}
              </Button>
            </div>
            {create.isError && (
              <p className="text-sm text-red-600">{(create.error as Error).message}</p>
            )}
          </form>
        </Card>
      )}

      {projectsQuery.isLoading && <Spinner label="Cargando proyectos…" />}
      {projectsQuery.data?.length === 0 && (
        <Card className="p-8 text-center text-sm text-slate-500">No hay proyectos todavía.</Card>
      )}
      {projectsQuery.data && projectsQuery.data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projectsQuery.data.map((p: Project) => {
            const st = PROJECT_STATUS[p.status] ?? { label: p.status, tone: "neutral" as const };
            return (
              <Link key={p.id} to={`/proyectos/${p.id}`}>
                <Card className="h-full p-5 transition hover:border-brand-300 hover:shadow-md">
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-slate-900">{p.name}</h3>
                    <Badge tone={st.tone}>{st.label}</Badge>
                  </div>
                  {p.description && (
                    <p className="mb-3 line-clamp-2 text-sm text-slate-500">{p.description}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <Badge tone="neutral">{p.area_name}</Badge>
                    {p.owner_name && <span>· {p.owner_name}</span>}
                    {p.due_date && (
                      <span>· vence {new Date(p.due_date).toLocaleDateString("es-CO")}</span>
                    )}
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
