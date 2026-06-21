import { Navigate, Outlet } from "react-router-dom";

import { useMe } from "../auth/useAuth";

export default function RequireAuth() {
  const me = useMe();

  if (me.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Cargando…
      </div>
    );
  }

  if (me.isError || !me.data) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
