import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BarChart3, ChevronDown, FolderKanban, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { type DevUser, devLogin, googleLoginUrl, listDevUsers, verify2fa } from "../api/auth";
import { useMe } from "../auth/useAuth";
import { Badge, Spinner } from "../components/ui";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-5 w-5" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

const FEATURES = [
  { icon: FolderKanban, title: "Cartera de proyectos", text: "Roadmap, áreas, sprints y entregas en un solo lugar." },
  { icon: BarChart3, title: "Analítica accionable", text: "Avance, riesgos y salud de cada iniciativa." },
  { icon: Sparkles, title: "Asistente con IA", text: "Resúmenes, tareas y reuniones desde tus documentos." },
];

const ERROR_MESSAGES: Record<string, string> = {
  domain: "Esa cuenta no pertenece al dominio de Invesa. Usa tu correo @invesa.com.",
  google: "No pudimos completar el inicio de sesión con Google. Inténtalo de nuevo.",
  not_registered: "Tu cuenta aún no está habilitada en Ágora. Pide a un administrador que te dé acceso.",
};

export default function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const me = useMe();
  const devUsers = useQuery({ queryKey: ["dev-users"], queryFn: listDevUsers, retry: false });
  const [showDev, setShowDev] = useState(false);

  const params = new URLSearchParams(window.location.search);
  const errorKey = params.get("error") ?? "";
  const error = ERROR_MESSAGES[errorKey];
  const [stage, setStage] = useState<"signin" | "2fa">(params.get("2fa") === "1" ? "2fa" : "signin");
  const [code, setCode] = useState("");

  const onAuthed = (user: NonNullable<ReturnType<typeof useMe>["data"]>) => {
    queryClient.setQueryData(["me"], user);
    navigate("/inicio", { replace: true });
  };

  const login = useMutation({
    mutationFn: (userId: number) => devLogin(userId),
    onSuccess: (res) => {
      if (res.needs_2fa) {
        setStage("2fa");
        return;
      }
      if (res.user) onAuthed(res.user);
    },
  });

  const verify = useMutation({
    mutationFn: () => verify2fa(code.trim()),
    onSuccess: (user) => onAuthed(user),
  });

  useEffect(() => {
    if (me.data && stage === "signin") navigate("/inicio", { replace: true });
  }, [me.data, stage, navigate]);

  return (
    <div className="flex min-h-screen bg-white">
      {/* Panel de marca */}
      <div className="relative hidden w-1/2 overflow-hidden bg-ink-gradient lg:flex lg:flex-col lg:justify-between">
        <div
          className="pointer-events-none absolute inset-0 opacity-90"
          style={{ background: "radial-gradient(120% 80% at 0% 0%, rgba(16,185,129,0.35) 0%, transparent 55%), radial-gradient(100% 80% at 100% 100%, rgba(13,148,136,0.30) 0%, transparent 55%)" }}
        />
        <div className="relative z-10 flex items-center gap-3 p-10">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-gradient text-lg font-bold text-white shadow-lg">
            Á
          </div>
          <div>
            <div className="text-lg font-semibold tracking-tight text-white">Ágora</div>
            <div className="text-xs text-slate-300">Invesa</div>
          </div>
        </div>

        <div className="relative z-10 px-10">
          <h2 className="max-w-md text-3xl font-bold leading-tight tracking-tight text-white">
            Gestión inteligente de proyectos para Invesa.
          </h2>
          <p className="mt-3 max-w-md text-sm text-slate-300">
            Una plataforma que cruza proyectos, documentos y datos de tu Workspace para que decidas con claridad.
          </p>
          <div className="mt-9 space-y-5">
            {FEATURES.map((f) => (
              <div key={f.title} className="flex items-start gap-3.5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 text-white ring-1 ring-white/15">
                  <f.icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{f.title}</div>
                  <div className="text-sm text-slate-300">{f.text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 p-10 text-xs text-slate-400">
          © {new Date().getFullYear()} Invesa · Plataforma interna
        </div>
      </div>

      {/* Panel de acceso */}
      <div className="flex w-full flex-col items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient text-base font-bold text-white">
              Á
            </div>
            <span className="text-lg font-semibold tracking-tight text-slate-900">Ágora</span>
          </div>

          {stage === "2fa" ? (
            <>
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">Verificación en dos pasos</h1>
              <p className="mt-1.5 text-sm text-slate-500">
                Ingresa el código de 6 dígitos de tu app de autenticación.
              </p>

              {verify.isError && (
                <div className="mt-5 rounded-xl border border-red-100 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
                  Código inválido o expirado. Inténtalo de nuevo.
                </div>
              )}

              <input
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && code.trim().length === 6) verify.mutate();
                }}
                inputMode="numeric"
                autoFocus
                placeholder="000000"
                className="mt-6 h-14 w-full rounded-xl border border-slate-300 bg-white text-center text-2xl font-semibold tracking-[0.4em] text-slate-900 placeholder:text-slate-300 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />

              <button
                type="button"
                onClick={() => verify.mutate()}
                disabled={code.trim().length !== 6 || verify.isPending}
                className="mt-4 flex h-12 w-full items-center justify-center rounded-xl bg-brand-600 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-50"
              >
                {verify.isPending ? "Verificando…" : "Verificar e ingresar"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStage("signin");
                  setCode("");
                  window.history.replaceState(null, "", "/login");
                }}
                className="mt-4 inline-flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-slate-700"
              >
                <ArrowLeft className="h-4 w-4" /> Volver
              </button>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">Bienvenido</h1>
              <p className="mt-1.5 text-sm text-slate-500">Inicia sesión para acceder a tu cartera de proyectos.</p>

              {error && (
                <div className="mt-5 rounded-xl border border-red-100 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
                  {error}
                </div>
              )}

              <a
                href={googleLoginUrl}
                className="mt-6 flex h-12 w-full items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                <GoogleIcon />
                Continuar con Google
              </a>

              <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-slate-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                Acceso restringido a cuentas <span className="font-medium text-slate-500">@invesa.com</span>
              </div>

              {devUsers.data && devUsers.data.length > 0 && (
                <div className="mt-8 border-t border-slate-100 pt-5">
                  <button
                    type="button"
                    onClick={() => setShowDev((v) => !v)}
                    className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-400 transition hover:text-slate-600"
                  >
                    Modo desarrollo (local)
                    <ChevronDown className={`h-4 w-4 transition ${showDev ? "rotate-180" : ""}`} />
                  </button>
                  {showDev && (
                    <div className="mt-3 space-y-2">
                      {devUsers.data.map((user: DevUser) => (
                        <button
                          key={user.id}
                          type="button"
                          onClick={() => login.mutate(user.id)}
                          disabled={login.isPending}
                          className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-2.5 text-left transition hover:border-brand-300 hover:bg-brand-50/40 disabled:opacity-50"
                        >
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                            {getInitials(user.name)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm font-medium text-slate-900">{user.name}</span>
                              <Badge tone={user.role === "admin" ? "brand" : "neutral"}>
                                {user.role === "admin" ? "Admin" : "Miembro"}
                              </Badge>
                            </div>
                            <div className="truncate text-xs text-slate-500">{user.email}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {devUsers.isLoading && (
                <div className="mt-6">
                  <Spinner label="Cargando…" />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
