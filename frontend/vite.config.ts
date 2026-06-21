import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  // Pre-optimiza las dependencias principales al arrancar para evitar el ciclo
  // "nueva dependencia descubierta -> recarga" a media sesión (que tumbaba el dev server).
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "@tanstack/react-query",
      "lucide-react",
      "recharts",
      "react-markdown",
      "remark-gfm",
    ],
  },
  server: {
    host: true,
    port: 5173,
    // Los bind-mounts de Docker en Windows no emiten eventos de archivo;
    // con polling el HMR detecta los cambios sin reiniciar el contenedor.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
