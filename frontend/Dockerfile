# syntax=docker/dockerfile:1

# ── Base: Node + pnpm (via corepack) ───────────────────────────────
FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm PATH="/pnpm:$PATH"
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
WORKDIR /app

# ── Dependencias ───────────────────────────────────────────────────
FROM base AS deps
COPY package.json ./
# Sin --frozen-lockfile en el primer build (aún no hay pnpm-lock.yaml).
# Tras el primer arranque: commitea pnpm-lock.yaml y usa --frozen-lockfile.
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install

# ── Dev: Vite dev server (código montado por volumen) ──────────────
FROM deps AS dev
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]

# ── Build: assets estáticos ────────────────────────────────────────
FROM deps AS build
COPY . .
RUN pnpm build

# ── Runtime: Nginx sirviendo la SPA ────────────────────────────────
FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
