#!/usr/bin/env bash
# ============================================================
# Ágora — deploy script (local → Linux production)
# ------------------------------------------------------------
# Usage:
#   ./deploy.sh                Build + ship + restart, with auto-rollback
#   ./deploy.sh --skip-build   Reuse existing local images (no docker compose build)
#   ./deploy.sh --rollback     Restore previous release on the server
#   ./deploy.sh --migrate-data Push CURRENT local DB into prod (one-time, overwrites prod DB)
#   ./deploy.sh --help         Show help
#
# Run from Git Bash. Will prompt for SSH password a few times during deploy
# (one per remote operation). Assumes the server already has, under DEPLOY_PATH,
# a production .env (secrets) — the deploy ships images + the compose files, never .env.
# ============================================================

set -euo pipefail

# ─────────────────────────── CONFIG (ajusta a tu servidor) ───────────────────────────
DEPLOY_HOST="root@mimir"          # p. ej. root@mi-servidor  (usuario@host SSH)
DEPLOY_PATH="/root/Agora"             # carpeta del proyecto en el servidor
HEALTHCHECK_PORT="8090"               # = FRONTEND_PORT del .env (puerto del nginx de Ágora)
HEALTHCHECK_PATH="/api/health"        # el nginx de Ágora proxya /api → backend
DB_CONTAINER="agora_postgres"         # = container_name del servicio db en prod
DB_USER="agora"                       # = POSTGRES_USER del .env de producción
DB_NAME="agora"                       # = POSTGRES_DB del .env de producción
HEALTHCHECK_TIMEOUT=120               # s de espera de /api/health antes de rollback
KEEP_RELEASES=2                       # copias tar.gz en releases/ (además de la actual)
KEEP_PREDEPLOY_DUMPS=5                # snapshots pg_dump conservados
BACKUPS_PATH_REMOTE="/srv/agora/backups/predeploy"
# deploy.sh vive en la raíz del repo → REPO_DIR es su propia carpeta.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR}"
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
# ────────────────────────────────────────────────────────────────

# ─── Output helpers ───
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[..]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[!!]${NC} $*"; }
err()  { echo -e "${RED}[XX]${NC} $*" >&2; }
die()  { err "$*"; exit 1; }

# ─── Args ───
ROLLBACK=false
SKIP_BUILD=false
MIGRATE_DATA=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rollback)     ROLLBACK=true;     shift ;;
    --skip-build)   SKIP_BUILD=true;   shift ;;
    --migrate-data) MIGRATE_DATA=true; shift ;;
    -h|--help)
      grep -E '^# (Usage|  |Run)' "${BASH_SOURCE[0]}" | sed 's/^# //'
      exit 0 ;;
    *) die "Unknown argument: $1 (use --help)" ;;
  esac
done

[[ "$DEPLOY_HOST" != *CHANGE-ME* ]] || die "Edita el bloque CONFIG: DEPLOY_HOST aún es CHANGE-ME."

# ─── State ───
TS="$(date +%Y%m%d-%H%M)"
TAR_NAME="agora-images-${TS}.tar.gz"
LOCAL_TAR="$(dirname "$SCRIPT_DIR")/${TAR_NAME}"   # el tar cae FUERA del repo
LOCAL_DUMP="$(dirname "$SCRIPT_DIR")/agora-localdump-${TS}.sql.gz"

cleanup() {
  [[ -f "$LOCAL_TAR" ]] && rm -f "$LOCAL_TAR" || true
  [[ -f "$LOCAL_DUMP" ]] && rm -f "$LOCAL_DUMP" || true
}
trap cleanup EXIT

# ─── SSH helpers — conexión directa por llamada ───
remote()    { ssh -o ConnectTimeout=15 -o ServerAliveInterval=15 "$DEPLOY_HOST" "$@"; }
remote_sh() { ssh -o ConnectTimeout=15 -o ServerAliveInterval=15 "$DEPLOY_HOST" 'bash -s'; }
check_ssh() {
  info "Comprobando SSH a $DEPLOY_HOST (pedirá contraseña)..."
  ssh -o ConnectTimeout=10 -o BatchMode=no "$DEPLOY_HOST" 'echo OK' >/dev/null \
    || die "No se llega a $DEPLOY_HOST. ¿VPN/red activa?"
  ok "SSH OK"
}

# ──────────────────────── ROLLBACK MODE ────────────────────────
if $ROLLBACK; then
  check_ssh
  PREV=$(remote "ls -1t ${DEPLOY_PATH}/releases/*.tar.gz 2>/dev/null | head -1") || true
  [[ -n "$PREV" ]] || die "No hay release previa en ${DEPLOY_PATH}/releases/"
  info "Rollback a: $PREV"
  remote_sh <<EOF
set -euo pipefail
cd "$DEPLOY_PATH"
cp "$PREV" agora-images.tar.gz
docker load < agora-images.tar.gz
docker compose ${COMPOSE_FILES[*]} up -d
EOF
  info "Esperando healthcheck..."
  for _ in $(seq 1 30); do
    remote "curl -fsS --max-time 5 http://localhost:${HEALTHCHECK_PORT}${HEALTHCHECK_PATH}" >/dev/null 2>&1 && { ok "Responde tras rollback"; exit 0; }
    sleep 2
  done
  die "NO responde tras rollback. Revisa:\n  ssh ${DEPLOY_HOST} 'cd ${DEPLOY_PATH} && docker compose ${COMPOSE_FILES[*]} logs --tail=50'"
fi

# ──────────────────────── MIGRATE DATA (una sola vez) ────────────────────────
# Lleva los datos LOCALES actuales a producción. Ejecutar DESPUÉS del primer
# ./deploy.sh (la base de prod debe existir). SOBREESCRIBE la base de prod.
if $MIGRATE_DATA; then
  [[ -d "$REPO_DIR" ]] || die "Repo no encontrado: $REPO_DIR"
  cd "$REPO_DIR"
  check_ssh
  warn "Esto SOBREESCRIBE la base de PRODUCCIÓN con tus datos LOCALES actuales."
  read -p "  Escribe MIGRAR para continuar: " -r; echo
  [[ "$REPLY" == "MIGRAR" ]] || die "Abortado"

  info "Volcando base local (${DB_NAME})..."
  docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner \
    | gzip > "$LOCAL_DUMP"
  ok "Dump local: $(du -h "$LOCAL_DUMP" | cut -f1)"

  info "Subiendo dump..."
  scp -o ConnectTimeout=15 "$LOCAL_DUMP" "${DEPLOY_HOST}:${DEPLOY_PATH}/migrate-localdump.sql.gz"

  info "Respaldando prod y restaurando (backend detenido durante la carga)..."
  remote_sh <<EOF
set -euo pipefail
cd "$DEPLOY_PATH"
mkdir -p "$BACKUPS_PATH_REMOTE"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" \
  | gzip > "${BACKUPS_PATH_REMOTE}/pre-migrate_\$(date +%Y%m%d_%H%M).sql.gz" || true
docker compose ${COMPOSE_FILES[*]} stop backend
gunzip -c migrate-localdump.sql.gz | docker exec -i "$DB_CONTAINER" psql -v ON_ERROR_STOP=0 -U "$DB_USER" -d "$DB_NAME" >/dev/null
rm -f migrate-localdump.sql.gz
docker compose ${COMPOSE_FILES[*]} up -d backend
EOF
  ok "Datos locales migrados a producción. (Respaldo previo en ${BACKUPS_PATH_REMOTE}/pre-migrate_*.sql.gz)"
  exit 0
fi

# ──────────────────────── PRE-CHECKS ────────────────────────
info "Pre-chequeos locales..."
[[ -d "$REPO_DIR" ]] || die "Repo no encontrado: $REPO_DIR"
cd "$REPO_DIR"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  warn "Rama actual '$CURRENT_BRANCH' (no 'main')."
  read -p "  ¿Desplegar igual desde esta rama? [y/N] " -n 1 -r; echo
  [[ $REPLY =~ ^[Yy]$ ]] || die "Abortado"
fi
git diff --quiet && git diff --cached --quiet || die "Árbol sucio. Commitea o stashea primero."
ok "Local OK (rama=$CURRENT_BRANCH, árbol limpio)"

check_ssh

# ──────────────────────── BUILD ────────────────────────
if ! $SKIP_BUILD; then
  info "Construyendo imágenes (target producción)..."
  docker compose "${COMPOSE_FILES[@]}" build
  ok "Build completo"
else
  info "Sin build (--skip-build)"
fi
for IMG in agora-backend:latest agora-frontend:latest; do
  docker image inspect "$IMG" >/dev/null 2>&1 || die "Imagen no encontrada local: $IMG (¿falló el build?)"
done

# ──────────────────────── SAVE ────────────────────────
info "Guardando imágenes en ${TAR_NAME}..."
docker save agora-backend:latest agora-frontend:latest | gzip > "$LOCAL_TAR"
TAR_SIZE=$(du -h "$LOCAL_TAR" | cut -f1)
ok "Tar: $TAR_SIZE"

# ──────────────────────── PRE-DEPLOY DB DUMP ────────────────────────
info "pg_dump de respaldo en el servidor..."
DUMP_TS="$(date +%Y%m%d_%H%M)"
remote_sh <<EOF
set -euo pipefail
mkdir -p "$BACKUPS_PATH_REMOTE"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "${BACKUPS_PATH_REMOTE}/postgres_${DUMP_TS}.sql.gz"
ls -1t "${BACKUPS_PATH_REMOTE}"/postgres_*.sql.gz | tail -n +$((KEEP_PREDEPLOY_DUMPS + 1)) | xargs -r rm
EOF
ok "Dump: ${BACKUPS_PATH_REMOTE}/postgres_${DUMP_TS}.sql.gz"

# ──────────────────────── UPLOAD (imágenes + compose) ────────────────────────
info "Subiendo ${TAR_SIZE} + archivos compose..."
remote "mkdir -p ${DEPLOY_PATH}/releases"
scp -o ConnectTimeout=15 "$LOCAL_TAR" docker-compose.yml docker-compose.prod.yml "${DEPLOY_HOST}:${DEPLOY_PATH}/"
ok "Subida completa"

# ──────────────────────── DEPLOY ────────────────────────
info "Cargando imágenes y reiniciando servicios..."
remote_sh <<EOF
set -euo pipefail
cd "$DEPLOY_PATH"
[[ -f .env ]] || { echo "ERROR: falta ${DEPLOY_PATH}/.env (secretos de producción)"; exit 1; }
[[ -f agora-images.tar.gz ]] && mv agora-images.tar.gz "releases/agora-images-prev-\$(date +%Y%m%d_%H%M).tar.gz"
mv "${TAR_NAME}" agora-images.tar.gz
docker load < agora-images.tar.gz
docker compose ${COMPOSE_FILES[*]} up -d
ls -1t releases/*.tar.gz 2>/dev/null | tail -n +$((KEEP_RELEASES + 1)) | xargs -r rm
docker image prune -f >/dev/null 2>&1 || true
EOF
ok "Deploy aplicado"

# ──────────────────────── HEALTHCHECK ────────────────────────
info "Sondeando http://localhost:${HEALTHCHECK_PORT}${HEALTHCHECK_PATH} (timeout ${HEALTHCHECK_TIMEOUT}s)..."
START=$(date +%s)
while true; do
  if remote "curl -fsS --max-time 5 http://localhost:${HEALTHCHECK_PORT}${HEALTHCHECK_PATH}" >/dev/null 2>&1; then
    ok "Healthcheck OK ($(( $(date +%s) - START ))s)"; break
  fi
  if (( $(date +%s) - START > HEALTHCHECK_TIMEOUT )); then
    err "Healthcheck NO pasó en ${HEALTHCHECK_TIMEOUT}s — rollback automático..."
    remote_sh <<EOF
set -euo pipefail
cd "$DEPLOY_PATH"
PREV=\$(ls -1t releases/*.tar.gz 2>/dev/null | head -1)
if [[ -n "\$PREV" ]]; then
  cp "\$PREV" agora-images.tar.gz; docker load < agora-images.tar.gz
  docker compose ${COMPOSE_FILES[*]} up -d
  echo "Rollback a \$PREV hecho."
else
  echo "ERROR: sin release previa — servicio puede estar caído."
  docker compose ${COMPOSE_FILES[*]} ps
fi
EOF
    die "Rollback automático ejecutado. Logs:\n  ssh ${DEPLOY_HOST} 'cd ${DEPLOY_PATH} && docker compose ${COMPOSE_FILES[*]} logs --tail=80'"
  fi
  sleep 3
done

info "Limpiando tar local..."
rm -f "$LOCAL_TAR"
ok "Deploy completo: ${TS}"
echo
echo "  Release en servidor: ${DEPLOY_PATH}/agora-images.tar.gz"
echo "  Releases previas   : ${DEPLOY_PATH}/releases/ (últimas ${KEEP_RELEASES})"
echo "  pg_dump            : ${BACKUPS_PATH_REMOTE}/postgres_${DUMP_TS}.sql.gz"
echo
echo "  Rollback:  $0 --rollback"
