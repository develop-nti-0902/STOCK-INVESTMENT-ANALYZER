#!/usr/bin/env bash
set -euo pipefail

# SQLite teardown script (Linux/macOS / Git Bash)
# Usage:
#   ./teardown_sqlite.sh [DB_FILE]
#   - If DB_FILE provided, it will be used. Otherwise uses SQLITE_DB_FILE, DATABASE_URL, or ./data/sqlite.db

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load .env if present (simple KEY=VALUE parsing)
if [[ -f "${REPO_ROOT}/.env" ]]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//')
    case "$key" in
      SQLITE_DB_FILE) [[ -z "${SQLITE_DB_FILE:-}" ]] && export SQLITE_DB_FILE="$value" ;;
      DATABASE_URL)  [[ -z "${DATABASE_URL:-}" ]] && export DATABASE_URL="$value" ;;
    esac
  done < "${REPO_ROOT}/.env"
fi

DB_FILE_ARG="${1:-}"
if [[ -n "$DB_FILE_ARG" ]]; then
  DB_FILE="$DB_FILE_ARG"
elif [[ -n "${SQLITE_DB_FILE:-}" ]]; then
  DB_FILE="$SQLITE_DB_FILE"
elif [[ -n "${DATABASE_URL:-}" ]]; then
  DB_FILE="$DATABASE_URL"
else
  DB_FILE="${REPO_ROOT}/data/sqlite.db"
fi

# If DB_FILE is a sqlite URL, strip prefix
if [[ "$DB_FILE" == sqlite:///* ]]; then
  DB_FILE="${DB_FILE#sqlite:///}"
fi

# If DB_FILE is relative, make absolute relative to repo root
if [[ "$DB_FILE" != /* ]]; then
  DB_FILE="${REPO_ROOT%/}/${DB_FILE}
"
  DB_FILE="$(cd "$(dirname "$DB_FILE")" && pwd)/$(basename "$DB_FILE")"
fi

echo "Using SQLite DB file: $DB_FILE"

# Detect Python command (same logic as other scripts)
if [[ -f ".venv/bin/python" ]]; then
  PYTHON_CMD=".venv/bin/python"
elif [[ -f "venv/bin/python" ]]; then
  PYTHON_CMD="venv/bin/python"
else
  PYTHON_CMD="python3"
fi

if [[ ! -f "$DB_FILE" ]]; then
  echo "[INFO] DB file does not exist: $DB_FILE — nothing to teardown"
  exit 0
fi

# Ensure alembic is available
"${PYTHON_CMD}" -m alembic --version &>/dev/null || {
  echo "[ERROR] Alembic not found. Install it: ${PYTHON_CMD} -m pip install alembic"
  exit 1
}

# Skipping Alembic downgrade: directly remove DB file

echo "Deleting DB file: $DB_FILE"
rm -f -- "$DB_FILE" || {
  echo "[ERROR] Failed to delete DB file: $DB_FILE"
  exit 1
}

echo "[SUCCESS] SQLite DB file removed: $DB_FILE"
exit 0
