# 0003 — El agente es lector y ejecutor

- **Estado:** Aceptada
- **Fecha:** 2026-06-20

## Contexto

El `CLAUDE.md` inicial planteaba la integración con Google como solo-lectura y el agente (Fase 4) como Q&A sobre datos estructurados. Se aclaró que la plataforma debe, además, **ejecutar acciones**: enviar correo, cargar/leer archivos de Drive y, sobre todo, crear reuniones en Calendar con enlace de Meet indicándole al agente en lenguaje natural qué usuarios invitar.

## Decisión

- El agente expone **dos clases de tools**: de **lectura** (SQL acotado y, en Fase 5, RAG) y de **acción** (crear evento de Calendar/Meet con asistentes, enviar correo, etc.).
- Las acciones con **efecto externo** pasan por **confirmación humana** antes de ejecutarse y quedan **auditadas**.
- Los **scopes de Google escalan** de solo-lectura (sincronización, Fase 3) a escritura (`calendar.events`, y `gmail.send` si el correo sale como el usuario) al activar las acciones (Fase 4+).
- La **autorización por área** acota también las acciones (sobre qué proyecto se actúa y a quién se invita).

## Consecuencias

- Hay que reservar la clave de cifrado de tokens (`TOKEN_ENCRYPTION_KEY`) y planear el refresco de tokens.
- En `backend/app/agent/` se separan por diseño las tools de lectura de las de acción.
- Decisión abierta para más adelante: el correo se envía **como el usuario** (Gmail API) o **como la plataforma** (SMTP/servicio transaccional). Afecta scopes y `.env`.

## Alternativas consideradas

- Agente solo de lectura (descartado: pierde la mitad del valor que pide negocio).
- Ejecutar acciones sin confirmación (descartado: riesgo de acciones irreversibles erróneas — correos, invitaciones).
