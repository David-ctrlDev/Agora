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

  return (
    <div className="flex items-center justify-between rounded-lg bg-slate-50 px-2.5 py-2">
      <span className="flex items-center gap-2 text-xs text-slate-600">
        <Cloud className="h-4 w-4 text-slate-400" />
        Google
        <span
          className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-500" : "bg-slate-300"}`}
        />
      </span>
      {connected ? (
        <button
          type="button"
          onClick={() => disconnect.mutate()}
          className="text-xs text-slate-400 transition hover:text-red-600"
        >
          desconectar
        </button>
      ) : (
        <button
          type="button"
          onClick={() => connect.mutate()}
          disabled={connect.isPending}
          className="text-xs font-medium text-brand-600 transition hover:underline"
        >
          conectar
        </button>
      )}
    </div>
  );
}
