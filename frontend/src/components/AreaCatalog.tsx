import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Plus, X } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  type AreaRequest,
  approveAreaRequest,
  areaCatalog,
  myAreaRequests,
  pendingAreaRequests,
  rejectAreaRequest,
  requestJoinArea,
  requestNewArea,
} from "../api/areaRequests";
import { useMe } from "../auth/useAuth";
import { Badge, Button, Card, Input, Spinner, Textarea } from "./ui";

const STATUS_TONE = { pending: "warning", approved: "success", rejected: "danger" } as const;
const STATUS_LABEL = { pending: "Pendiente", approved: "Aprobada", rejected: "Rechazada" } as const;

export default function AreaCatalog() {
  const qc = useQueryClient();
  const me = useMe();
  const isAdmin = me.data?.role === "admin";

  const catalog = useQuery({ queryKey: ["area-catalog"], queryFn: areaCatalog });
  const mine = useQuery({ queryKey: ["area-requests-mine"], queryFn: myAreaRequests });
  const pending = useQuery({ queryKey: ["area-requests-pending"], queryFn: pendingAreaRequests });

  const invalidate = () => {
    for (const key of ["area-catalog", "area-requests-mine", "area-requests-pending", "areas"]) {
      void qc.invalidateQueries({ queryKey: [key] });
    }
  };

  const join = useMutation({ mutationFn: requestJoinArea, onSuccess: invalidate });
  const approve = useMutation({ mutationFn: approveAreaRequest, onSuccess: invalidate });
  const reject = useMutation({ mutationFn: (id: number) => rejectAreaRequest(id), onSuccess: invalidate });

  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const reqNew = useMutation({
    mutationFn: () => requestNewArea(newName.trim(), newDesc.trim() || undefined),
    onSuccess: () => {
      invalidate();
      setNewName("");
      setNewDesc("");
    },
  });
  const submitNew = (e: FormEvent) => {
    e.preventDefault();
    if (newName.trim()) reqNew.mutate();
  };

  const areas = catalog.data ?? [];
  const myReqs = mine.data ?? [];
  const toApprove = pending.data ?? [];

  return (
    <div className="space-y-8">
      {/* Solicitudes por aprobar (líder/admin) */}
      {toApprove.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">
            Solicitudes por aprobar ({toApprove.length})
          </h2>
          <div className="space-y-2">
            {toApprove.map((r: AreaRequest) => (
              <div
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-3"
              >
                <div className="text-sm">
                  <span className="font-medium text-slate-800">{r.requester_name}</span>
                  <span className="text-slate-500">
                    {r.kind === "join"
                      ? ` quiere unirse a «${r.area_name}»`
                      : ` propone el área «${r.proposed_name}»`}
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => approve.mutate(r.id)} disabled={approve.isPending}>
                    <Check className="h-3.5 w-3.5" /> Aprobar
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => reject.mutate(r.id)} disabled={reject.isPending}>
                    <X className="h-3.5 w-3.5" /> Rechazar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Catálogo de áreas */}
      <Card className="p-5">
        <h2 className="mb-1 text-sm font-semibold text-slate-700">Explorar áreas</h2>
        <p className="mb-4 text-xs text-slate-500">
          Solicita unirte a un área para ver sus proyectos. La aprobación la da su líder o un admin.
        </p>
        {catalog.isLoading ? (
          <Spinner />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {areas.map((a) => (
              <div key={a.id} className="flex flex-col rounded-xl border border-slate-200 p-4">
                <div className="flex-1">
                  <div className="font-medium text-slate-800">{a.name}</div>
                  {a.description && (
                    <p className="mt-1 line-clamp-2 text-xs text-slate-500">{a.description}</p>
                  )}
                  <div className="mt-2 text-xs text-slate-400">
                    {a.member_count} miembro{a.member_count === 1 ? "" : "s"}
                    {a.leads.length > 0 && ` · líder: ${a.leads.join(", ")}`}
                  </div>
                </div>
                <div className="mt-3">
                  {a.is_member ? (
                    <Badge tone="success" dot>
                      Miembro
                    </Badge>
                  ) : a.pending ? (
                    <Badge tone="warning" dot>
                      Solicitud enviada
                    </Badge>
                  ) : (
                    <Button size="sm" onClick={() => join.mutate(a.id)} disabled={join.isPending}>
                      Solicitar unirme
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Solicitar área nueva (no-admin: el admin la crea directo) */}
      {!isAdmin && (
        <Card className="p-5">
          <h2 className="mb-1 text-sm font-semibold text-slate-700">¿No está tu área?</h2>
          <p className="mb-4 text-xs text-slate-500">
            Propón una nueva; un administrador la creará y quedarás como su líder.
          </p>
          <form onSubmit={submitNew} className="space-y-3">
            <Input
              label="Nombre del área"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="p. ej. Logística"
            />
            <Textarea
              label="Descripción (opcional)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              rows={2}
            />
            <Button type="submit" disabled={!newName.trim() || reqNew.isPending}>
              <Plus className="h-4 w-4" /> Solicitar área nueva
            </Button>
          </form>
        </Card>
      )}

      {/* Mis solicitudes */}
      {myReqs.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Mis solicitudes</h2>
          <div className="space-y-2">
            {myReqs.map((r: AreaRequest) => (
              <div
                key={r.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 px-4 py-2.5 text-sm"
              >
                <span className="text-slate-700">
                  {r.kind === "join" ? `Unirme a «${r.area_name}»` : `Crear «${r.proposed_name}»`}
                </span>
                <Badge tone={STATUS_TONE[r.status]} dot>
                  {STATUS_LABEL[r.status]}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
