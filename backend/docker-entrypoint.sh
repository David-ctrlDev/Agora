#!/bin/sh
set -e

export PYTHONPATH=/app

echo "[entrypoint] Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

# Asegura los administradores iniciales (BOOTSTRAP_ADMIN_EMAILS). No-op si está vacío.
python -m app.bootstrap_admins || echo "[entrypoint] bootstrap de admins omitido (continuo)"

if [ "${ENV:-development}" = "development" ] && [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "[entrypoint] Sembrando datos de desarrollo..."
  python -m app.seed_dev || echo "[entrypoint] seed omitido (continuo)"
fi

echo "[entrypoint] Iniciando aplicación: $*"
exec "$@"
