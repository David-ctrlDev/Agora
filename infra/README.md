# infra

Configuraciones auxiliares de infraestructura.

- `n8n/` — (Fase 6) workflows exportados y configuración de n8n para jobs programados y notificaciones. n8n corre como contenedor bajo el perfil `tools` de `docker-compose.yml` (no arranca por defecto).

> La configuración de Nginx que sirve la SPA en producción vive junto al frontend (`frontend/nginx.conf`) para mantener el contexto de build self-contained.
