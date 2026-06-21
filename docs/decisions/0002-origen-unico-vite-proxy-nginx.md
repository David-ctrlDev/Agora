# 0002 — Mismo origen: proxy de Vite en dev, Nginx en prod

- **Estado:** Aceptada
- **Fecha:** 2026-06-20

## Contexto

El login usa JWT en cookie httpOnly (Google OAuth). El manejo de cookies y CORS depende de si el frontend y la API comparten origen.

## Decisión

Servir frontend y API bajo el **mismo origen**:

- **Desarrollo:** el dev server de Vite hace proxy de `/api` al backend (`http://backend:8000` en la red de compose). El navegador solo ve `http://localhost:5173`.
- **Producción:** Nginx sirve la SPA estática y hace proxy de `/api` al backend (`frontend/nginx.conf`).

## Consecuencias

- **Sin CORS** y cookies `SameSite=Lax` simples; menos superficie de error en el login.
- El frontend siempre llama a rutas relativas `/api/...`.
- En producción la cookie va con `Secure=true` (HTTPS).

## Alternativas consideradas

- Orígenes separados + CORS + cookies `SameSite=None; Secure`: más fricción y más fácil de configurar mal.
