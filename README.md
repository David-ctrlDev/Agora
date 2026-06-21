# Ágora

Plataforma interna de gestión de proyectos de **Invesa**, con una capa de agente (IA) que cruza señales de GitHub, Google Workspace y el estado de los proyectos para resumir, hacer seguimiento, detectar riesgos y **ejecutar acciones** (crear reuniones en Calendar/Meet, enviar notificaciones).

> Visión completa y plan por fases: [`CLAUDE.md`](./CLAUDE.md). Decisiones técnicas: [`docs/decisions/`](./docs/decisions/).

## Stack

- **Backend:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Postgres 16 + pgvector · gestionado con `uv`.
- **Frontend:** React 18 · Vite · TypeScript (strict) · Tailwind · TanStack Query · gestionado con `pnpm`.
- **Infra:** Docker Compose · n8n (perfil `tools`).

## Requisitos

- Docker y Docker Compose.

## Arranque

```bash
cp .env.example .env          # ajusta los valores
docker compose up --build
```

- Frontend: <http://localhost:5173>
- API (vía proxy de Vite, mismo origen): <http://localhost:5173/api/health>
- API directa: <http://localhost:8000/api/health>
- Postgres: `localhost:5432`

Para levantar también n8n (jobs/notificaciones, fases posteriores):

```bash
docker compose --profile tools up
```

## Estructura

```
backend/    API FastAPI (PM core + agente en fases futuras)
frontend/   SPA React
infra/      configs auxiliares (n8n)
docs/       documentación y decisiones (ADRs)
```

## Estado

**Fase 0 — andamiaje.** Aún sin modelos de datos, autenticación ni features de negocio (ver roadmap en [`CLAUDE.md`](./CLAUDE.md)).
