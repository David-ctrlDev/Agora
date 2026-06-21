# Ágora

Plataforma interna de gestión de proyectos de **Invesa** con una **capa de agente (IA)**
que cruza señales de GitHub, Google Workspace y el estado interno de los proyectos para
resumir, hacer seguimiento, detectar riesgos y **ejecutar acciones** (crear reuniones en
Calendar/Meet, enviar notificaciones) — siempre con confirmación humana y autorización por área.

> Visión y plan por fases: [`CLAUDE.md`](./CLAUDE.md) · Decisiones técnicas: [`docs/decisions/`](./docs/decisions/)

## Stack

- **Backend:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Postgres 16 + **pgvector** · `uv`
- **Frontend:** React 18 · Vite · TypeScript (strict) · Tailwind · TanStack Query · `pnpm`
- **Infra:** Docker Compose · n8n (perfil `tools`)

## Arranque (sin pasos manuales)

```bash
cp .env.example .env
docker compose up --build
```

El backend **aplica las migraciones y siembra datos de demo** automáticamente al arrancar.

- Frontend: <http://localhost:5173>
- API (vía proxy): <http://localhost:5173/api/health> · API directa: <http://localhost:8000/api/health>

### Acceso (login de desarrollo)

No requiere Google. En la pantalla de login entra como uno de los usuarios sembrados:

| Usuario | Rol | Áreas |
|---|---|---|
| Wilder Serna | Admin global | todas |
| Ana Gómez | Miembro | Producción (lead) |
| Carlos Ruiz | Miembro | Ambiental, Comercial |

## Funcionalidades

- **Áreas** y **autorización por área** (admin global ve todo; miembros, solo sus áreas) — aplicada en el backend.
- **Proyectos** (CRUD por área, miembros) y **Tareas** (tablero por estado, prioridad, responsable, comentarios) + "Mis tareas".
- **GitHub** (mock): vincular repos, actividad (commits/PRs/releases/issues) y **webhook firmado (HMAC)**.
- **Google Workspace** (mock): Drive + Calendar por proyecto; **tokens OAuth cifrados** (Fernet).
- **Agente** (lector + ejecutor): preguntas sobre datos estructurados (tools SQL acotadas por área) y **RAG**; acciones (crear reunión Meet, enviar correo) con **confirmación humana** y auditoría.
- **RAG** en pgvector: ingesta + embeddings + búsqueda semántica.
- **Notificaciones proactivas**: detección de riesgos (tareas vencidas/bloqueadas, entregas en riesgo) segmentada por área; disparable por n8n.

> **Sin llamadas externas:** GitHub, Google, Gemini y el correo usan **proveedores mock**
> deterministas detrás de interfaces; los adaptadores reales se activan con credenciales
> (`*_provider=real`). Ver [`docs/decisions/0005-proveedores-mock.md`](./docs/decisions/0005-proveedores-mock.md).

## Pruebas

```bash
docker compose exec backend pytest        # backend (BD de test efímera)
docker compose exec frontend pnpm typecheck
```

## n8n (opcional)

```bash
docker compose --profile tools up
```

Importa `infra/n8n/agora-notificaciones.json` (dispara la detección de riesgos por schedule).

## Estructura

```
backend/    API FastAPI · app/{core,models,schemas,routers,services,agent,rag,integrations}
frontend/   SPA React · src/{api,components,pages,auth}
infra/      n8n
docs/       documentación y decisiones (ADRs)
```

## Estado

Fases 0–6 implementadas (autocontenido, con proveedores mock). Ver `CLAUDE.md`.
