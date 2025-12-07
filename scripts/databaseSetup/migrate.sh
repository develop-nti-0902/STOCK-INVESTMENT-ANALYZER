#!/usr/bin/env bash
# =============================================================================
# Alembic migration wrapper (Linux/macOS)
# Location: scripts/databaseSetup/migrate.sh
# Usage: migrate.sh [upgrade|downgrade|history|current] [<target>] [--sql]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load .env from repo root if present
if [[ -f "${REPO_ROOT}/.env" ]]; then
  echo "[INFO] Loading env from ${REPO_ROOT}/.env"
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    case "$key" in
      DATABASE_URL) [[ -z "${DATABASE_URL:-}" ]] && export DATABASE_URL="$value" ;;
      PGHOST) [[ -z "${PGHOST:-}" ]] && export PGHOST="$value" ;;
      PGPORT) [[ -z "${PGPORT:-}" ]] && export PGPORT="$value" ;;
      PGUSER) [[ -z "${PGUSER:-}" ]] && export PGUSER="$value" ;;
      PGPASSWORD) [[ -z "${PGPASSWORD:-}" ]] && export PGPASSWORD="$value" ;;
      DB_NAME) [[ -z "${DB_NAME:-}" ]] && export DB_NAME="$value" ;;
      DB_USER) [[ -z "${DB_USER:-}" ]] && export DB_USER="$value" ;;
      DB_PASSWORD) [[ -z "${DB_PASSWORD:-}" ]] && export DB_PASSWORD="$value" ;;
    esac
  done < "${REPO_ROOT}/.env"
fi

# Usage
if [[ ${#@} -eq 0 ]]; then
  echo "Usage: $0 [upgrade|downgrade|history|current] [<target>] [--sql]"
  exit 1
fi

CMD=${1:-upgrade}
TARGET=${2:-head}
SQL_FLAG=""
if [[ "${@: -1}" == "--sql" ]]; then
  SQL_FLAG="--sql"
  # If --sql present and TARGET is not specified, keep head
fi

echo "[INFO] Running alembic command: ${CMD} ${TARGET} ${SQL_FLAG}"

# Prepare DATABASE_URL if pieces provided
if [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -n "${PGHOST:-}" && -n "${PGPORT:-}" && -n "${DB_NAME:-}" && -n "${DB_USER:-}" && -n "${DB_PASSWORD:-}" ]]; then
    export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${PGHOST}:${PGPORT}/${DB_NAME}"
    echo "[INFO] Constructed DATABASE_URL from environment variables"
  fi
fi

if ! command -v poetry &> /dev/null; then
  echo "[WARN] poetry not found in PATH; attempting to run alembic directly"
  ALEMBIC_CMD="alembic -c ${REPO_ROOT}/alembic.ini ${CMD} ${TARGET} ${SQL_FLAG}"
  echo "[INFO] $ALEMBIC_CMD"
  eval "$ALEMBIC_CMD"
else
  poetry run alembic -c "${REPO_ROOT}/alembic.ini" ${CMD} ${TARGET} ${SQL_FLAG}
fi

echo "[SUCCESS] alembic command finished"
exit 0
