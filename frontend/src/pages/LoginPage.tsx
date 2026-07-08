import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { type DevUser, devLogin, googleLoginUrl, listDevUsers, verify2fa } from "../api/auth";
import { useMe } from "../auth/useAuth";

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

const ERROR_MESSAGES: Record<string, string> = {
  domain: "Esa cuenta no pertenece al dominio de Invesa. Usa tu correo @invesa.com.",
  google: "No pudimos completar el inicio de sesión con Google. Inténtalo de nuevo.",
  not_registered: "Tu cuenta aún no está habilitada en Ágora. Pide acceso a un administrador.",
};

const STYLES = `
@keyframes agora-drift-a { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(8%, -6%) scale(1.15); } }
@keyframes agora-drift-b { 0%,100% { transform: translate(0,0) scale(1.1); } 50% { transform: translate(-7%, 5%) scale(1); } }
@keyframes agora-drift-c { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(5%, 8%) scale(1.2); } }
@keyframes agora-rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
`;

export default function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const me = useMe();
  const devUsers = useQuery({ queryKey: ["dev-users"], queryFn: listDevUsers, retry: false });
  const [showDev, setShowDev] = useState(false);

  const params = new URLSearchParams(window.location.search);
  const error = ERROR_MESSAGES[params.get("error") ?? ""];
  const expired = params.get("expired");
  const notice =
    error ??
    (expired === "idle"
      ? "Tu sesión se cerró por inactividad. Vuelve a iniciar sesión."
      : expired
        ? "Tu sesión expiró. Vuelve a iniciar sesión."
        : null);
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0a0d1f] px-4">
      <style>{STYLES}</style>

      {/* Aurora animada */}
      <div
        className="pointer-events-none absolute -left-40 -top-40 h-[42rem] w-[42rem] rounded-full opacity-50 blur-3xl"
        style={{ background: "radial-gradient(circle, #10b981 0%, transparent 65%)", animation: "agora-drift-a 16s ease-in-out infinite" }}
      />
      <div
        className="pointer-events-none absolute -bottom-48 -right-40 h-[40rem] w-[40rem] rounded-full opacity-45 blur-3xl"
        style={{ background: "radial-gradient(circle, #0d9488 0%, transparent 65%)", animation: "agora-drift-b 19s ease-in-out infinite" }}
      />
      <div
        className="pointer-events-none absolute left-1/3 top-1/2 h-[30rem] w-[30rem] rounded-full opacity-30 blur-3xl"
        style={{ background: "radial-gradient(circle, #6366f1 0%, transparent 70%)", animation: "agora-drift-c 22s ease-in-out infinite" }}
      />
      {/* Velo + textura sutil */}
      <div className="pointer-events-none absolute inset-0 bg-[#0a0d1f]/40" />

      <div
        className="relative z-10 w-full max-w-md rounded-3xl border border-white/10 bg-white/[0.07] p-8 shadow-2xl backdrop-blur-2xl sm:p-10"
        style={{ animation: "agora-rise 0.5s ease-out both" }}
      >
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient text-2xl font-bold text-white shadow-lg ring-1 ring-white/20">
            Á
          </div>
          <div className="mt-3 text-xl font-semibold tracking-tight text-white">Ágora</div>
          <div className="text-xs text-slate-400">Plataforma de proyectos · Invesa</div>
        </div>

        {stage === "2fa" ? (
          <div className="text-center">
            <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-400/15 text-emerald-300 ring-1 ring-emerald-300/20">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h1 className="text-lg font-semibold text-white">Verificación en dos pasos</h1>
            <p className="mt-1 text-sm text-slate-400">Ingresa el código de 6 dígitos de tu app.</p>

            {verify.isError && (
              <div className="mt-4 rounded-xl border border-red-400/20 bg-red-500/10 px-3.5 py-2.5 text-sm text-red-200">
                Código inválido o expirado.
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
              className="mt-5 h-14 w-full rounded-xl border border-white/15 bg-white/5 text-center text-2xl font-semibold tracking-[0.4em] text-white placeholder:text-white/25 focus:border-emerald-400/50 focus:outline-none focus:ring-2 focus:ring-emerald-400/20"
            />
            <button
              type="button"
              onClick={() => verify.mutate()}
              disabled={code.trim().length !== 6 || verify.isPending}
              className="mt-4 flex h-12 w-full items-center justify-center rounded-xl bg-brand-gradient text-sm font-semibold text-white shadow-lg transition hover:brightness-110 disabled:opacity-50"
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
              className="mx-auto mt-4 inline-flex items-center gap-1.5 text-sm text-slate-400 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" /> Volver
            </button>
          </div>
        ) : (
          <>
            <h1 className="text-center text-lg font-semibold text-white">Bienvenido de nuevo</h1>
            <p className="mt-1 text-center text-sm text-slate-400">Accede a tu cartera de proyectos.</p>

            {notice && (
              <div className="mt-5 rounded-xl border border-red-400/20 bg-red-500/10 px-3.5 py-2.5 text-sm text-red-200">
                {notice}
              </div>
            )}

            <a
              href={googleLoginUrl}
              className="mt-6 flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-white text-sm font-semibold text-slate-700 shadow-lg transition hover:bg-slate-50"
            >
              <GoogleIcon />
              Continuar con Google
            </a>

            <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5" />
              Solo cuentas <span className="font-medium text-slate-300">@invesa.com</span>
            </div>

            {devUsers.data && devUsers.data.length > 0 && (
              <div className="mt-7 border-t border-white/10 pt-5">
                <button
                  type="button"
                  onClick={() => setShowDev((v) => !v)}
                  className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-400 transition hover:text-slate-200"
                >
                  Modo desarrollo (local)
                  <ChevronDown className={`h-4 w-4 transition ${showDev ? "rotate-180" : ""}`} />
                </button>
                {showDev && (
                  <div className="mt-3 max-h-60 space-y-2 overflow-y-auto">
                    {devUsers.data.map((user: DevUser) => (
                      <button
                        key={user.id}
                        type="button"
                        onClick={() => login.mutate(user.id)}
                        disabled={login.isPending}
                        className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-2.5 text-left transition hover:bg-white/10 disabled:opacity-50"
                      >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-slate-200">
                          {getInitials(user.name)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium text-white">{user.name}</div>
                          <div className="truncate text-xs text-slate-400">{user.email}</div>
                        </div>
                        <span className="shrink-0 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                          {user.role === "admin" ? "Admin" : "Miembro"}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <div className="absolute bottom-5 z-10 text-center text-xs text-slate-500">
        Proyectos · Analítica · Asistente con IA — © {new Date().getFullYear()} Invesa
      </div>
    </div>
  );
}
