#!/usr/bin/env bash
# =============================================================================
# PostgreSQL development database teardown (Linux/macOS)
# Location: scripts/databaseSetup/teardown_db.sh
# Usage: Run this script directly or call it from other setup scripts
# =============================================================================

set -euo pipefail

# This script uses the local psql client to drop the database, user, and tablespace,
# and optionally removes the data directory created during setup.
# NOTE: The teardown removes the entire database specified by DB_NAME.
#       Because the database is dropped, deleting individual tables is unnecessary
#       and this script does not attempt to drop tables inside the database.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration priority (highest to lowest):
# 1) Positional arguments: PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER
# 2) Environment variables
# 3) .env file at repository root (if present)

# Store positional arguments temporarily to apply them after .env loading
ARG1="${1:-}"
ARG2="${2:-}"
ARG3="${3:-}"
ARG4="${4:-}"
ARG5="${5:-}"
ARG6="${6:-}"
ARG7="${7:-}"
ARG8="${8:-}"

# Load .env file from the repo root if present.
# Expected file: ${REPO_ROOT}/.env
if [[ -f "${REPO_ROOT}/.env" ]]; then
    echo "[INFO] Loading env from ${REPO_ROOT}/.env"
    # Export variables from .env file (only if not already set)
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        # Remove leading/trailing whitespace and quotes
        key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        # Only set if not already defined
        case "$key" in
            PGHOST) [[ -z "${PGHOST:-}" ]] && export PGHOST="$value" ;;
            PGPORT) [[ -z "${PGPORT:-}" ]] && export PGPORT="$value" ;;
            PGUSER) [[ -z "${PGUSER:-}" ]] && export PGUSER="$value" ;;
            PGPASSWORD) [[ -z "${PGPASSWORD:-}" ]] && export PGPASSWORD="$value" ;;
            DB_NAME) [[ -z "${DB_NAME:-}" ]] && export DB_NAME="$value" ;;
            DB_USER) [[ -z "${DB_USER:-}" ]] && export DB_USER="$value" ;;
            DB_DATA_DIR) [[ -z "${DB_DATA_DIR:-}" ]] && export DB_DATA_DIR="$value" ;;
            SKIP_TABLESPACE) [[ -z "${SKIP_TABLESPACE:-}" ]] && export SKIP_TABLESPACE="$value" ;;
        esac
    done < "${REPO_ROOT}/.env"
fi

# Positional arguments override other settings (highest priority). Example usage:
# teardown_db.sh PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER
[[ -n "$ARG1" ]] && export PGHOST="$ARG1"
[[ -n "$ARG2" ]] && export PGPORT="$ARG2"
[[ -n "$ARG3" ]] && export PGUSER="$ARG3"
[[ -n "$ARG4" ]] && export PGPASSWORD="$ARG4"
[[ -n "$ARG5" ]] && export DB_NAME="$ARG5"
[[ -n "$ARG6" ]] && export DB_USER="$ARG6"

# 7th argument: DB_DATA_DIR (or boolean to indicate SKIP_TABLESPACE).
# If the 7th arg is 1/true/yes then SKIP_TABLESPACE is set and DB_DATA_DIR is cleared.
if [[ -n "$ARG7" ]]; then
    if [[ "$ARG7" =~ ^(1|true|yes|TRUE|YES)$ ]]; then
        export SKIP_TABLESPACE="$ARG7"
        unset DB_DATA_DIR
    else
        export DB_DATA_DIR="$ARG7"
        unset SKIP_TABLESPACE
        [[ -n "$ARG8" ]] && export SKIP_TABLESPACE="$ARG8"
    fi
fi

echo ""
echo "========================================"
echo "Database teardown (Linux/macOS)"
echo "========================================"
echo ""
echo "[INFO] This teardown will DROP the entire database. Individual table drops are skipped."

# Check for psql in PATH
echo "[1/6] Checking PostgreSQL installation..."

if ! command -v psql &> /dev/null; then
    echo "[ERROR] psql (PostgreSQL client) not found in PATH."
    echo "Install PostgreSQL client or add it to PATH, then retry."
    exit 1
fi

echo "Using PGHOST=${PGHOST} PGPORT=${PGPORT} PGUSER=${PGUSER}"

echo "Dropping database and user (may ask for postgres password)..."

# Validate required variables
echo "[2/6] Validating required variables..."

if [[ -z "${PGHOST:-}" ]]; then
    echo "[ERROR] PGHOST not set. Provide via .env, environment, or first positional argument."
    exit 1
fi
if [[ -z "${PGPORT:-}" ]]; then
    echo "[ERROR] PGPORT not set. Provide via .env, environment, or second positional argument."
    exit 1
fi
if [[ -z "${PGUSER:-}" ]]; then
    echo "[ERROR] PGUSER not set. Provide via .env, environment, or third positional argument."
    exit 1
fi
if [[ -z "${DB_NAME:-}" ]]; then
    echo "[ERROR] DB_NAME not set. Provide via .env, environment, or fifth positional argument."
    exit 1
fi
if [[ -z "${DB_USER:-}" ]]; then
    echo "[ERROR] DB_USER not set. Provide via .env, environment, or sixth positional argument."
    exit 1
fi
if [[ -z "${PGPASSWORD:-}" ]]; then
    echo "[ERROR] PGPASSWORD not set. Provide via .env, environment, or fourth positional argument."
    exit 1
fi

# Check DB_DATA_DIR vs SKIP_TABLESPACE relationship
if [[ -z "${DB_DATA_DIR:-}" ]] && [[ -z "${SKIP_TABLESPACE:-}" ]]; then
    echo "[ERROR] DB_DATA_DIR not set. Provide via .env, environment, or seventh positional argument."
    exit 1
fi
if [[ -n "${DB_DATA_DIR:-}" ]] && [[ -n "${SKIP_TABLESPACE:-}" ]]; then
    echo "[ERROR] DB_DATA_DIR is set but SKIP_TABLESPACE is also specified; these are mutually exclusive."
    exit 1
fi

# Drop database if exists
echo "[3/6] Dropping database if exists..."

DB_EXISTS=$(psql -U "${PGUSER}" -h "${PGHOST}" -t -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" 2>&1 | tr -d '[:space:]')
if [[ "$DB_EXISTS" == "1" ]]; then
    # Disconnect existing connections before dropping
    psql -U "${PGUSER}" -h "${PGHOST}" -c "REVOKE CONNECT ON DATABASE \"${DB_NAME}\" FROM public;" 2>/dev/null || echo "[WARN] Could not revoke connects"
    psql -U "${PGUSER}" -h "${PGHOST}" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" 2>/dev/null || echo "[WARN] Could not terminate connections"
    psql -U "${PGUSER}" -h "${PGHOST}" -c "DROP DATABASE IF EXISTS \"${DB_NAME}\";" 2>/dev/null || {
        echo "[ERROR] Failed to drop database ${DB_NAME}"
        exit 1
    }
    echo "Database ${DB_NAME} dropped successfully"
else
    echo "Database ${DB_NAME} does not exist; skipping drop"
fi

echo "[4/6] Dropping tablespace (unless skipped)..."
if [[ -n "${SKIP_TABLESPACE:-}" ]]; then
    echo "[INFO] SKIP_TABLESPACE is set; skipping tablespace drop"
else
    # Drop tablespace (use IF EXISTS for simplicity)
    echo "Attempting to drop tablespace stock_data_space..."
    psql -U "${PGUSER}" -h "${PGHOST}" -c "DROP TABLESPACE IF EXISTS stock_data_space;" 2>/dev/null && {
        echo "Tablespace dropped or did not exist"
    } || {
        echo "[WARN] Could not drop tablespace (may be in use or insufficient privileges)"
    }
fi

echo "[5/6] Removing tablespace directory (if specified)..."
if [[ -n "${SKIP_TABLESPACE:-}" ]]; then
    echo "[INFO] SKIP_TABLESPACE is set; skipping directory removal"
elif [[ -n "${DB_DATA_DIR:-}" ]]; then
    DB_FULL_PATH="${DB_DATA_DIR}/${DB_NAME}"
    if [[ -d "$DB_FULL_PATH" ]]; then
        echo "[INFO] DB_DATA_DIR specified: $DB_FULL_PATH"
        echo "[INFO] Automatic directory removal is disabled for safety. Remove the directory manually if desired."
        echo "[INFO] To remove: rm -rf \"$DB_FULL_PATH\""
    else
        echo "Directory $DB_FULL_PATH not found; nothing to remove"
    fi
else
    echo "DB_DATA_DIR not provided; no directory to remove"
fi

# Drop user if exists
echo "[6/6] Dropping user (if exists) and finishing..."

echo "Attempting to drop user ${DB_USER}..."
psql -U "${PGUSER}" -h "${PGHOST}" -c "DO \$\$ BEGIN IF EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '${DB_USER}') THEN ALTER ROLE ${DB_USER} WITH NOLOGIN; DROP OWNED BY ${DB_USER} CASCADE; DROP ROLE IF EXISTS ${DB_USER}; RAISE NOTICE 'User dropped'; ELSE RAISE NOTICE 'User does not exist'; END IF; END\$\$;" 2>/dev/null && {
    echo "User dropped or did not exist"
} || {
    echo "[WARN] Could not drop user (may need superuser privileges)"
}

echo ""
echo "[SUCCESS] Database teardown script finished."
exit 0
