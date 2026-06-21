# syntax=docker/dockerfile:1

# ── Base: Python + uv ──────────────────────────────────────────────
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

# ── Dependencias (capa cacheada) ───────────────────────────────────
FROM base AS deps
COPY pyproject.toml ./
# Sin --frozen en el primer build (aún no hay uv.lock commiteado).
# Tras el primer arranque: commitea uv.lock y añade --frozen para builds reproducibles.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# ── Dev: hot-reload (el código se monta por volumen) ───────────────
FROM deps AS dev
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Runtime: producción ────────────────────────────────────────────
FROM base AS runtime
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
