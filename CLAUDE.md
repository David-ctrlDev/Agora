# Contexto del proyecto — Plataforma de gestión de proyectos con agente IA

Este documento es el contexto global del proyecto. Léelo completo antes de escribir cualquier código. Define **qué vamos a construir, con qué stack, cómo está organizado y en qué orden**. No implementes nada todavía: trabajaremos de forma incremental y yo te indicaré la tarea concreta de cada sesión (ver sección "Modo de trabajo" al final).

---

## 1. Objetivo

Construir una plataforma interna de gestión de proyectos para **Invesa** (empresa de agroquímicos). Más allá del CRUD típico de proyectos/tareas, el diferenciador es una **capa de inteligencia (agente RAG + LLM)** que cruza señales de varias fuentes —GitHub, Google Workspace y el estado interno de los proyectos— para producir resúmenes, seguimientos, detección de riesgos y notificaciones útiles.

Es una herramienta de **uso interno**: no necesita multi-tenancy, facturación ni onboarding público. Los usuarios autentican con sus cuentas de Google Workspace de la empresa.

La plataforma se organiza por **áreas** (las áreas/departamentos de Invesa: Producción, Ambiental, RRHH, Comercial, IT, etc.). Cada proyecto pertenece a un área, y cada usuario tiene acceso a una o varias áreas. La visibilidad de proyectos, los resúmenes del agente y las notificaciones se filtran según las áreas del usuario; un rol de administrador global puede ver todas las áreas. Esto es transversal a todo el sistema, no un módulo aislado.

## 2. Principios de diseño

- **El agente es el diferenciador, pero todo es de primera clase.** El PM core (proyectos, tareas, estados) y las integraciones (correo, Drive, Calendar) deben ser completos y pulidos por sí mismos; la capa de síntesis **y de acción** del agente es lo que eleva la plataforma por encima de un tablero típico.
- **Arquitectura híbrida de datos.** Los datos estructurados (tareas, fechas, commits, estados) se consultan directamente con SQL vía herramientas del agente — **no** se vectorizan. Solo el contenido no estructurado (documentos, actas, descripciones de PRs/issues) va a RAG. Meter todo en el vector store da respuestas vagas y desactualizadas.
- **Segmentación por área de extremo a extremo.** El área es la unidad organizativa central. Toda consulta de proyectos/tareas, todo contexto del agente y toda notificación deben filtrarse por las áreas a las que el usuario tiene acceso. La autorización por área se aplica en el backend, nunca solo en el frontend.
- **Incremental y entregable por fases.** Cada fase debe dejar algo usable en producción antes de pasar a la siguiente.
- **Seguridad y gobernanza de datos desde el inicio** (ver sección 10).

## 3. Stack tecnológico (fijo)

**Backend**
- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2.0 (modo async) + asyncpg
- Alembic para migraciones
- Pydantic v2 (schemas) + pydantic-settings (configuración por entorno)
- Autenticación: Google OAuth2 (Authlib), sesión vía JWT en cookie httpOnly
- httpx para llamadas a APIs externas (GitHub, Google)
- LLM: **Google Gemini** vía el SDK `google-genai`. Modelo de chat: `gemini-2.0-flash` (ajustable). Embeddings: `text-embedding-004`.

**Base de datos**
- PostgreSQL 16 con extensión **pgvector** (imagen `pgvector/pgvector:pg16`). Unifica datos relacionales y vector store en una sola pieza.

**Frontend**
- React 18 + Vite + TypeScript (modo strict)
- Tailwind CSS
- TanStack Query (data fetching y cache)
- React Router
- Estado ligero con Zustand o Context

**Infraestructura / orquestación**
- Docker + docker-compose para todo el entorno de desarrollo
- **n8n** (contenedor aparte) para jobs programados, sincronización periódica y disparo de notificaciones en fases posteriores
- Webhooks de GitHub entran directo al backend de FastAPI

## 4. Arquitectura (capas)

```
Fuentes externas        GitHub  ·  Google Workspace (Drive, Calendar, Gmail)
        │
Capa de sincronización  Webhooks GitHub + jobs programados en n8n
        │
Almacén                 Postgres + pgvector (relacional + embeddings)
        │
Backend (FastAPI)       PM core API  ·  Agente (RAG + LLM Gemini)
        │
Salidas                 Frontend React  ·  Notificaciones (Slack / correo)
```

El flujo de datos va de las fuentes externas hacia el usuario: la sincronización escribe en Postgres, el backend lee de ahí y sirve al frontend y a las notificaciones.

## 5. Modelo de datos

### Fase 1 (crear ahora cuando se indique)
- `areas` — id, name, slug (único), description, is_active, created_at
- `users` — id, google_sub (único), email, name, avatar_url, role (admin/member; `admin` = administrador global con acceso a todas las áreas), default_area_id (FK areas, nullable), is_active, created_at
- `user_areas` — user_id (FK), area_id (FK), area_role (lead/member); PK compuesta. Define a qué áreas pertenece cada usuario y su rol dentro de cada una
- `projects` — id, name, description, area_id (FK areas, NOT NULL), status (planned/active/on_hold/done/archived), owner_id (FK users), start_date, due_date, created_at, updated_at
- `project_members` — project_id (FK), user_id (FK), role (owner/editor/viewer); PK compuesta. Permite acceso fino dentro del área (o acceso puntual cruzado, si un admin lo concede)
- `tasks` — id, project_id (FK), title, description, status (todo/in_progress/blocked/done), priority (low/medium/high), assignee_id (FK users, nullable), due_date, created_at, updated_at
- `task_comments` — id, task_id (FK), author_id (FK), body, created_at

**Regla de visibilidad:** un usuario ve los proyectos de las áreas a las que pertenece (vía `user_areas`); un `admin` global ve todos. `project_members` solo restringe o amplía dentro de ese marco. Esta regla se implementa como dependencia/filtro reutilizable en el backend y se aplica a cada endpoint que devuelva proyectos, tareas, contexto del agente o notificaciones.

### Fases futuras (documentar, NO crear aún)
- `oauth_tokens` — tokens de Google por usuario, **cifrados en reposo**
- `github_repos` — vínculo repo ↔ project
- `github_events` — commits, PRs, releases, issues cacheados
- `google_documents` — docs/eventos de Drive y Calendar vinculados a proyectos
- `documents` / `document_chunks` — chunks de contenido no estructurado con columna `vector(768)` para embeddings de Gemini
- `notifications` — cola y registro de notificaciones enviadas
- `agent_conversations` / `agent_messages` — historial del agente conversacional

## 6. Integraciones (fases 2 y 3)

**GitHub (Fase 2, solo lectura primero)**
- Implementar como **GitHub App** sobre la organización de Invesa (acceso granular + webhooks), no como token personal.
- Eventos a escuchar: `push`, `pull_request`, `release`, `issues`.
- Verificar la **firma HMAC** de cada webhook entrante.
- Vincular repos a proyectos para mostrar actividad por proyecto.

**Google Workspace (Fase 3)**
- OAuth2 con el dominio de Invesa restringido (`hd`).
- Scopes mínimos y de solo lectura al inicio: Drive (metadata + lectura de archivos), Calendar (eventos). Gmail opcional y posterior.
- Tokens por usuario, cifrados; refrescar cuando expiren.
- Los scopes **escalan a escritura** cuando se implementen las acciones del agente (Fase 4+): `calendar.events` para crear reuniones con Meet e invitados, y `gmail.send` si el correo se envía como el usuario. La sincronización inicial se mantiene en solo-lectura y se sube el scope al activar cada acción. Ver `docs/decisions/0003-agente-lector-y-ejecutor.md`.

## 7. El agente (fases 4 y 5)

Diseño híbrido sobre Gemini con function calling:
- **Fase 4 — solo datos estructurados.** El agente usa *tools* que ejecutan consultas SQL acotadas (estado de proyecto, tareas vencidas, actividad reciente). Sin RAG todavía. Esto ya entrega la mayor parte del valor de "seguimiento inteligente".
- **Fase 5 — RAG.** Ingesta de documentos no estructurados → chunking → embeddings (Gemini) → `document_chunks` en pgvector. El retriever alimenta al LLM junto con los datos estructurados.

El agente conversacional con razonamiento multipaso vive en **código Python**, no en n8n. n8n se reserva para lo programado y las notificaciones.

**Las tools del agente reciben siempre el contexto de áreas del usuario** y restringen sus consultas a esas áreas. El agente nunca debe exponer datos de un área a la que el usuario no tiene acceso, ni siquiera en resúmenes agregados.

**El agente es lector y ejecutor.** Además de consultar (tools de lectura sobre SQL y, en Fase 5, RAG), expone *tools de acción* con efecto hacia afuera: crear una reunión en Calendar con enlace de Meet y los asistentes que el usuario indique en lenguaje natural, o enviar correo. Toda acción con efecto externo (crear reunión, invitar personas, enviar correo) pasa por **confirmación humana** antes de ejecutarse y queda **auditada**. La autorización por área acota también las acciones. Ver `docs/decisions/0003-agente-lector-y-ejecutor.md`.

## 8. Notificaciones (fase 6)

Detección proactiva de riesgos y resúmenes: por ejemplo "proyecto sin actividad de commits + entrega cercana", resúmenes semanales de avance, alertas de tareas bloqueadas. Disparadas por jobs de n8n que consultan al backend; salida a Slack y/o correo. Las notificaciones y resúmenes se segmentan por área: cada usuario recibe solo lo de sus áreas, y se pueden generar resúmenes por área dirigidos a su `lead`.

## 9. Roadmap por fases

0–1. **Scaffolding + PM core + áreas + login con Google.** Monorepo, docker-compose operativo, entidades de Fase 1, gestión de áreas (CRUD de áreas y asignación de usuarios a áreas), CRUD de proyectos/tareas con filtrado por área, autenticación con Google Workspace (dominio restringido) y autorización por área. Sin IA.
2. **Integración GitHub** (solo lectura): GitHub App, webhooks, actividad por proyecto.
3. **Integración Google Workspace**: Drive + Calendar vinculados a proyectos.
4. **Agente v1**: resúmenes y Q&A sobre datos estructurados vía function calling.
5. **RAG**: embeddings de documentos en pgvector.
6. **Notificaciones proactivas**: detección de riesgos y resúmenes automáticos.

> **Estado de implementación (2026-06-20):** las fases 1–6 están implementadas de
> forma autocontenida, con **proveedores mock** para lo externo (sin red): ver
> `docs/decisions/0005-proveedores-mock.md`. El acceso usa un **login de desarrollo**;
> Google OAuth real, GitHub App real y Gemini real quedan tras interfaz, activables
> por configuración + credenciales.

## 10. Seguridad y gobernanza

- **Datos a Gemini.** El contenido enviado al LLM sale a un tercero (Google). Minimiza PII en los prompts y pendiente confirmar política interna de Invesa antes de enviar contenido sensible al RAG.
- **Autorización por área aplicada en el backend.** Cada endpoint que devuelva proyectos, tareas, contexto del agente o notificaciones debe filtrar por las áreas del usuario autenticado mediante una dependencia reutilizable. No confiar nunca en el frontend para ocultar datos de otras áreas.
- Tokens OAuth de Google **cifrados en reposo**; nunca en logs.
- Login restringido al dominio de Invesa (`hd` en OAuth).
- Verificación de firma en webhooks de GitHub.
- Secretos solo vía variables de entorno (`.env`), nunca en el repositorio. Incluir siempre `.env.example`.
- No registrar secretos ni tokens en logs.

## 11. Estructura del repositorio (monorepo)

```
/
├── backend/
│   ├── app/
│   │   ├── core/          # config, db, security, dependencias
│   │   ├── models/        # modelos SQLAlchemy
│   │   ├── schemas/       # schemas Pydantic
│   │   ├── routers/       # endpoints FastAPI
│   │   ├── services/      # lógica de negocio
│   │   ├── agent/         # (fase 4+) tools, retriever, cliente Gemini
│   │   └── main.py
│   ├── alembic/           # migraciones
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/           # cliente + hooks de TanStack Query
│   │   ├── components/
│   │   ├── pages/
│   │   ├── store/
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── infra/                 # configs auxiliares (n8n, etc.)
├── docs/                  # documentación y decisiones (ADRs)
├── docker-compose.yml
├── .env.example
├── README.md
└── CLAUDE.md              # este documento
```

## 12. Convenciones de desarrollo

- **Código en inglés** (identificadores, comentarios). La documentación de negocio puede ir en español.
- Toda migración de esquema **siempre** vía Alembic; nunca DDL manual.
- Tipado estricto: TypeScript en modo strict; type hints en Python.
- Tests: pytest (backend) y Vitest (frontend); al menos smoke tests por feature.
- Commits convencionales (`feat:`, `fix:`, `chore:`...).
- Cada feature debe poder levantarse con `docker compose up` sin pasos manuales ocultos.

## 13. Modo de trabajo

**Trabajaremos de forma incremental y bajo mi dirección.** Este documento te da la visión completa para que tomes decisiones coherentes, pero:

- **No implementes fases futuras hasta que te lo pida explícitamente.** Conoces el destino; no corras hacia él.
- Cada sesión te indicaré la tarea concreta. Antes de escribir código, confirma brevemente qué vas a hacer y espera mi visto bueno si hay decisiones de diseño abiertas.
- Mantén el alcance de cada cambio acotado a lo solicitado.
- Cuando una decisión técnica afecte fases posteriores, señálalo antes de avanzar.

**Para empezar:** confirma que entendiste el plan, no escribas código todavía, y propón la estructura inicial del repositorio y el contenido de `docker-compose.yml`, `.env.example` y los `Dockerfile`. A partir de ahí iré indicando la siguiente parte.
