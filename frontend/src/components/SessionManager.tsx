import { useCallback, useEffect, useRef, useState } from "react";

import { logout } from "../api/auth";
import { Button, Modal } from "./ui";

// Inactividad tras la cual se cierra la sesión. Se avisa 1 min antes.
// (Cámbialo a 8 * 60 * 1000 si se quería 8 minutos en vez de 8 horas.)
const IDLE_MS = 8 * 60 * 60 * 1000; // 8 horas
const WARN_MS = 60 * 1000; // aviso 1 minuto antes

/** Cierra la sesión por inactividad, con un aviso previo para seguir conectado. */
export default function SessionManager() {
  const [warning, setWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(Math.round(WARN_MS / 1000));
  const warningRef = useRef(false);
  const warnTimer = useRef<number | undefined>(undefined);
  const outTimer = useRef<number | undefined>(undefined);
  const tick = useRef<number | undefined>(undefined);

  const clearAll = () => {
    window.clearTimeout(warnTimer.current);
    window.clearTimeout(outTimer.current);
    window.clearInterval(tick.current);
  };

  const doLogout = useCallback(async () => {
    clearAll();
    try {
      await logout();
    } catch {
      /* salimos igual */
    }
    window.location.assign("/login?expired=idle");
  }, []);

  const arm = useCallback(() => {
    clearAll();
    warningRef.current = false;
    setWarning(false);
    warnTimer.current = window.setTimeout(() => {
      warningRef.current = true;
      setSecondsLeft(Math.round(WARN_MS / 1000));
      setWarning(true);
      tick.current = window.setInterval(() => setSecondsLeft((s) => (s > 0 ? s - 1 : 0)), 1000);
    }, IDLE_MS - WARN_MS);
    outTimer.current = window.setTimeout(doLogout, IDLE_MS);
  }, [doLogout]);

  useEffect(() => {
    const events = ["mousemove", "keydown", "mousedown", "scroll", "touchstart"];
    let last = 0;
    const onActivity = () => {
      const now = Date.now();
      if (now - last < 1500) return; // throttle
      last = now;
      if (!warningRef.current) arm(); // durante el aviso, solo "Seguir conectado" reinicia
    };
    arm();
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
      clearAll();
    };
  }, [arm]);

  return (
    <Modal open={warning} onClose={arm} title="Tu sesión está por cerrarse" size="md">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Por seguridad cerraremos tu sesión por inactividad en{" "}
          <span className="font-semibold tabular-nums text-slate-900">{secondsLeft} s</span>.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={doLogout}>
            Cerrar sesión
          </Button>
          <Button onClick={arm}>Seguir conectado</Button>
        </div>
      </div>
    </Modal>
  );
}
