# 0005 — Proveedores de integración: mock en desarrollo, real tras interfaz

- **Estado:** Aceptada
- **Fecha:** 2026-06-20

## Contexto

El desarrollo se hace sin llamadas externas (sin credenciales de GitHub, Google
ni Gemini, y sin enviar correos reales). Aun así, todas las fases deben quedar
funcionales y demostrables en local.

## Decisión

- Cada integración vive **detrás de una interfaz** con dos implementaciones:
  un **proveedor de desarrollo (mock)** determinista y sin red, y un **adaptador
  real** (esqueleto) que se activa por configuración (`*_provider = "real"`).
- **GitHub:** mock genera commits/PRs/releases/issues; el webhook real se verifica
  por HMAC. **Google:** mock de Drive/Calendar; tokens OAuth **cifrados** (Fernet).
  **Gemini:** el agente usa un **stub de LLM determinista** (function-calling por
  heurística); los **embeddings** son locales (hashing) con dimensión 768 (igual
  que `text-embedding-004`).
- **Acciones del agente** (crear reunión Meet, enviar correo) y **notificaciones**
  van a un **outbox en BD** (auditado), sin envío real. Las acciones requieren
  **confirmación humana**.
- **Login:** se usa un **login de desarrollo**; el flujo de Google OAuth queda
  implementado pero inactivo hasta tener credenciales.
- `docker compose up` es autosuficiente: el backend **aplica migraciones y siembra
  datos** al arrancar (entrypoint).

## Consecuencias

- Todo el producto se ejecuta y prueba en local sin servicios externos.
- Pasar a real = poner credenciales + cambiar el flag de proveedor; el esquema y
  los contratos no cambian (p. ej. embeddings ya son de 768).
- La política de datos a Gemini (sección 10 de `CLAUDE.md`) debe confirmarse antes
  de activar el proveedor real.
