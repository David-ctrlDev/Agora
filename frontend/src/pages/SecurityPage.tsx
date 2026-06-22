import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";

import { type TwoFactorSetup, disable2fa, enable2fa, setup2fa } from "../api/auth";
import { useMe } from "../auth/useAuth";
import { Badge, Button, PageHeader, Panel, Spinner } from "../components/ui";

function CodeInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
      inputMode="numeric"
      placeholder="000000"
      className="h-11 w-36 rounded-xl border border-slate-300 bg-white text-center text-lg font-semibold tracking-[0.3em] text-slate-900 placeholder:text-slate-300 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
    />
  );
}

export default function SecurityPage() {
  const me = useMe();
  const qc = useQueryClient();
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [code, setCode] = useState("");
  const [disableCode, setDisableCode] = useState("");

  const enabled = me.data?.twofa_enabled ?? false;

  const start = useMutation({ mutationFn: setup2fa, onSuccess: (d) => setSetup(d) });
  const enable = useMutation({
    mutationFn: () => enable2fa(code.trim()),
    onSuccess: (u) => {
      qc.setQueryData(["me"], u);
      setSetup(null);
      setCode("");
    },
  });
  const disable = useMutation({
    mutationFn: () => disable2fa(disableCode.trim()),
    onSuccess: (u) => {
      qc.setQueryData(["me"], u);
      setDisableCode("");
    },
  });

  if (me.isLoading) return <Spinner label="Cargando…" />;

  return (
    <div className="max-w-2xl space-y-5">
      <PageHeader
        eyebrow="Cuenta"
        title="Seguridad"
        description="Protege tu acceso con verificación en dos pasos."
      />

      <Panel
        title="Verificación en dos pasos (2FA)"
        subtitle="Con una app de autenticación (Google Authenticator, Authy, Microsoft Authenticator…)"
        actions={
          <Badge tone={enabled ? "success" : "neutral"} dot>
            {enabled ? "Activo" : "Inactivo"}
          </Badge>
        }
      >
        {enabled ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-700">
              <ShieldCheck className="h-4 w-4" /> El 2FA está activo. Te pediremos un código al iniciar sesión.
            </div>
            <p className="text-sm text-slate-500">
              Para desactivarlo, ingresa un código actual de tu app de autenticación.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <CodeInput value={disableCode} onChange={setDisableCode} />
              <Button
                variant="danger"
                onClick={() => disable.mutate()}
                disabled={disableCode.length !== 6 || disable.isPending}
              >
                {disable.isPending ? "Desactivando…" : "Desactivar 2FA"}
              </Button>
            </div>
            {disable.isError && <p className="text-sm text-red-600">Código inválido. Inténtalo de nuevo.</p>}
          </div>
        ) : !setup ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Añade una capa extra de seguridad: además de tu inicio de sesión, pediremos un código temporal de tu
              app de autenticación.
            </p>
            <Button onClick={() => start.mutate()} disabled={start.isPending}>
              <ShieldCheck className="h-4 w-4" /> {start.isPending ? "Generando…" : "Activar 2FA"}
            </Button>
          </div>
        ) : (
          <div className="space-y-5">
            <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-600">
              <li>Escanea el código QR con tu app de autenticación.</li>
              <li>Ingresa el código de 6 dígitos que muestra la app para confirmar.</li>
            </ol>
            <div className="flex flex-wrap items-center gap-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
                <QRCodeSVG value={setup.otpauth_uri} size={168} />
              </div>
              <div className="text-sm">
                <div className="text-slate-500">¿No puedes escanear? Ingresa esta clave manualmente:</div>
                <code className="mt-1.5 inline-block break-all rounded-lg bg-slate-100 px-2.5 py-1.5 font-mono text-xs text-slate-700">
                  {setup.secret}
                </code>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <CodeInput value={code} onChange={setCode} />
              <Button onClick={() => enable.mutate()} disabled={code.length !== 6 || enable.isPending}>
                {enable.isPending ? "Activando…" : "Confirmar y activar"}
              </Button>
              <Button variant="ghost" onClick={() => setSetup(null)}>
                Cancelar
              </Button>
            </div>
            {enable.isError && (
              <p className="text-sm text-red-600">Código inválido, revisa la hora del dispositivo e inténtalo de nuevo.</p>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
