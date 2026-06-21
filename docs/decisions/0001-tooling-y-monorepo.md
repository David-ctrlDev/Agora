# 0001 — Monorepo y tooling de base

- **Estado:** Aceptada
- **Fecha:** 2026-06-20

## Contexto

Arrancamos el proyecto y hay que fijar el gestor de dependencias del backend, el del frontend y la forma de empaquetar en Docker. El stack (FastAPI, React/Vite, Postgres) ya está fijado en `CLAUDE.md`.

## Decisión

- **Monorepo** con `backend/`, `frontend/`, `infra/` y `docs/`.
- **Backend con `uv`**: rápido, un solo binario, lockfile reproducible (`uv.lock`) y excelente caché de capas en Docker.
- **Frontend con `pnpm`** (vía corepack): rápido, eficiente en disco y lockfile estricto.
- **Dockerfiles multi-stage** con targets `dev` (hot-reload, código montado por volumen) y `runtime` (build optimizado, usuario no-root). `docker-compose` usa el target `dev` por defecto.

## Consecuencias

- `docker compose up` levanta todo el entorno sin pasos manuales.
- En el primer build aún no hay lockfiles commiteados; los Dockerfiles instalan sin `--frozen`. Tras el primer arranque se commitean `uv.lock` y `pnpm-lock.yaml` y se cambia a instalación congelada para builds reproducibles.

## Alternativas consideradas

- Backend: Poetry (más lento/pesado en Docker) o pip + requirements (sin resolución avanzada).
- Frontend: npm o yarn.
