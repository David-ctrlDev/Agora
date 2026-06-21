#!/bin/sh
set -e

export PYTHONPATH=/app

echo "[entrypoint] Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

if [ "${ENV:-development}" = "development" ] && [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "[entrypoint] Sembrando datos de desarrollo..."
  python -m app.seed_dev || echo "[entrypoint] seed omitido (continuo)"
fi

echo "[entrypoint] Iniciando aplicación: $*"
exec "$@"
