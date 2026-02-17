#!/usr/bin/env bash
set -euo pipefail

# SQLite database setup and apply Alembic migrations (Linux/macOS / Git Bash)
# Location: scripts/databaseSetup/setup_sqlite.sh
# Usage:
#   ./setup_sqlite.sh [DB_FILE]
#   - If DB_FILE is provided it will be used (absolute or relative path).
#   - Otherwise use .env variable SQLITE_DB_FILE or default: ./data/sqlite.db

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load .env if present (simple KEY=VALUE parsing). Only set if not already defined.
if [[ -f "${REPO_ROOT}/.env" ]]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//')
    case "$key" in
      SQLITE_DB_FILE) [[ -z "${SQLITE_DB_FILE:-}" ]] && export SQLITE_DB_FILE="$value" ;;
      DATABASE_URL)  [[ -z "${DATABASE_URL:-}" ]] && export DATABASE_URL="$value" ;;
      SQLITE_JOURNAL_MODE) [[ -z "${SQLITE_JOURNAL_MODE:-}" ]] && export SQLITE_JOURNAL_MODE="$value" ;;
      SQLITE_SYNCHRONOUS) [[ -z "${SQLITE_SYNCHRONOUS:-}" ]] && export SQLITE_SYNCHRONOUS="$value" ;;
      SQLITE_TIMEOUT) [[ -z "${SQLITE_TIMEOUT:-}" ]] && export SQLITE_TIMEOUT="$value" ;;
      SQLITE_FOREIGN_KEYS) [[ -z "${SQLITE_FOREIGN_KEYS:-}" ]] && export SQLITE_FOREIGN_KEYS="$value" ;;
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

# If DB_FILE is a sqlite URL (sqlite:///...), strip the prefix to get the file path
if [[ "$DB_FILE" == sqlite:///* ]]; then
  DB_FILE="${DB_FILE#sqlite:///}"
fi

# Ensure directory exists
mkdir -p "$(dirname "$DB_FILE")"

# Try to create the SQLite database file if it doesn't exist.
if [[ ! -f "$DB_FILE" ]]; then
  # Prefer system sqlite3 if available, otherwise create via Python
  if command -v sqlite3 &>/dev/null; then
    sqlite3 "$DB_FILE" "VACUUM;" || true
  else
    ${PYTHON_CMD:-python3} - <<PY
import sqlite3, os
os.makedirs(os.path.dirname(r"$DB_FILE"), exist_ok=True)
sqlite3.connect(r"$DB_FILE").close()
PY
  fi
fi

# Resolve absolute path for SQLAlchemy URL
DB_DIR="$(cd "$(dirname "$DB_FILE")" && pwd)"
DB_BASENAME="$(basename "$DB_FILE")"
ABS_PATH="$DB_DIR/$DB_BASENAME"


# Detect Python command (same logic as other scripts)
if [[ -f ".venv/bin/python" ]]; then
  PYTHON_CMD=".venv/bin/python"
elif [[ -f "venv/bin/python" ]]; then
  PYTHON_CMD="venv/bin/python"
else
  PYTHON_CMD="python3"
fi

echo "Using SQLite DB file: $ABS_PATH"

# If DATABASE_URL not set, set it to point to this SQLite file
: "${DATABASE_URL:=}"
# If an existing DATABASE_URL points to SQLite, normalize/override it to the
# absolute file we prepared. This fixes cases where .env contains
# 'sqlite:///home/...' (which is treated as a relative path) instead of the
# correct absolute form 'sqlite:////home/...'.
if [[ "${DATABASE_URL:-}" == sqlite://* ]]; then
  export DATABASE_URL="sqlite:///$ABS_PATH"
  echo "Overwrote existing SQLite DATABASE_URL -> $DATABASE_URL"
elif [[ -z "${DATABASE_URL:-}" ]]; then
  export DATABASE_URL="sqlite:///$ABS_PATH"
  echo "Exported DATABASE_URL=$DATABASE_URL"
fi

# Diagnostic: ensure the DB file exists and is accessible to the current user
echo "Checking DB file and permissions..."
if [[ ! -e "$ABS_PATH" ]]; then
  echo "DB file does not exist, attempting to create: $ABS_PATH"
  if mkdir -p "$(dirname "$ABS_PATH")" 2>/dev/null && touch "$ABS_PATH" 2>/dev/null; then
    echo "Created DB file: $ABS_PATH"
  else
    echo "Could not create DB file with touch, trying via Python..."
    if ! "${PYTHON_CMD}" - <<PY
import sqlite3, os, sys
try:
    os.makedirs(os.path.dirname(r"$ABS_PATH"), exist_ok=True)
    sqlite3.connect(r"$ABS_PATH").close()
except Exception as e:
    print('PYTHON_CREATE_FAILED', e, file=sys.stderr)
    sys.exit(2)
PY
    then
      echo "[ERROR] Failed to create DB file: $ABS_PATH" >&2
      ls -ld "$(dirname "$ABS_PATH")" || true
      exit 1
    fi
  fi
fi

# Show directory and file permissions to help diagnose "unable to open database file"
echo "Directory listing:"; ls -ld "$(dirname "$ABS_PATH")" || true
echo "File listing:"; ls -l "$ABS_PATH" || true

# Try a quick sqlite3 access (if sqlite3 binary exists) to validate openability
if command -v sqlite3 &>/dev/null; then
  sqlite3 "$ABS_PATH" "PRAGMA user_version;" >/dev/null 2>&1 || echo "Warning: sqlite3 failed to open $ABS_PATH"
fi

# Check alembic
"${PYTHON_CMD}" -m alembic --version &>/dev/null || {
  echo "[ERROR] Alembic not found. Install it: ${PYTHON_CMD} -m pip install alembic"
  exit 1
}

echo "Running Alembic migrations (upgrade heads)..."
(
  cd "$REPO_ROOT" && \
  "${PYTHON_CMD}" -m alembic -c "${REPO_ROOT}/alembic.ini" upgrade heads
) || {
  echo "[ERROR] Alembic migration failed"
  exit 1
}

echo "[SUCCESS] SQLite DB ready: $ABS_PATH"
exit 0
