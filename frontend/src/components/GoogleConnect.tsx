import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cloud } from "lucide-react";

import { googleConnect, googleDisconnect, googleStatus } from "../api/google";

export default function GoogleConnect() {
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ["google-status"], queryFn: googleStatus });
  const connected = status.data?.connected ?? false;

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["google-status"] });
  const connect = useMutation({ mutationFn: googleConnect, onSuccess: invalidate });
  const disconnect = useMutation({ mutationFn: googleDisconnect, onSuccess: invalidate });

  const provider = status.data?.provider;
  const handleConnect = () => {
    if (provider === "real") {
      // OAuth real: el navegador navega a Google para autorizar.
      window.location.href = "/api/auth/google/login";
    } else {
      connect.mutate();
    }
  };

  if (!connected) {
    return (
      <button
        type="button"
        onClick={handleConnect}
        disabled={connect.isPending}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-xs font-semibold text-brand-700 transition hover:bg-brand-100 disabled:opacity-60"
      >
        <Cloud className="h-4 w-4" />
        {connect.isPending ? "Conectando…" : "Conectar Google Workspace"}
      </button>
    );
  }

  return (
    <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2 text-xs">
      <span className="flex items-center gap-2 font-semibold text-emerald-700">
        <Cloud className="h-4 w-4" /> Google conectado
      </span>
      <button
        type="button"
        onClick={() => disconnect.mutate()}
        className="text-emerald-600/70 transition hover:text-red-600"
      >
        desconectar
      </button>
    </div>
  );
}
