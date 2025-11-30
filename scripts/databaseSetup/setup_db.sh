#!/usr/bin/env bash
# =============================================================================
# PostgreSQL development database setup (Linux/macOS)
# Location: scripts/databaseSetup/setup_db.sh
# Usage: Run this script directly or call it from other setup scripts
# =============================================================================

set -euo pipefail

# This script uses the local psql client to create the database and user,
# and applies the initial schema from `create_stock_tables.sql` and
# `create_management_tables.sql` if present.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
STOCK_SQL="${SCRIPT_DIR}/sql/create_stock_tables.sql"
MGMT_SQL="${SCRIPT_DIR}/sql/create_management_tables.sql"

# Configuration priority (highest to lowest):
# 1) Positional arguments: PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER DB_PASSWORD
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
ARG9="${9:-}"

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
            DB_PASSWORD) [[ -z "${DB_PASSWORD:-}" ]] && export DB_PASSWORD="$value" ;;
            DB_DATA_DIR) [[ -z "${DB_DATA_DIR:-}" ]] && export DB_DATA_DIR="$value" ;;
            SKIP_TABLESPACE) [[ -z "${SKIP_TABLESPACE:-}" ]] && export SKIP_TABLESPACE="$value" ;;
        esac
    done < "${REPO_ROOT}/.env"
fi

# Positional arguments override other settings (highest priority). Example usage:
# setup_db.sh PGHOST PGPORT PGUSER PGPASSWORD DB_NAME DB_USER DB_PASSWORD
[[ -n "$ARG1" ]] && export PGHOST="$ARG1"
[[ -n "$ARG2" ]] && export PGPORT="$ARG2"
[[ -n "$ARG3" ]] && export PGUSER="$ARG3"
[[ -n "$ARG4" ]] && export PGPASSWORD="$ARG4"
[[ -n "$ARG5" ]] && export DB_NAME="$ARG5"
[[ -n "$ARG6" ]] && export DB_USER="$ARG6"
[[ -n "$ARG7" ]] && export DB_PASSWORD="$ARG7"

# 8th argument: DB_DATA_DIR (or boolean to indicate SKIP_TABLESPACE).
# If the 8th arg is 1/true/yes then SKIP_TABLESPACE is set and DB_DATA_DIR is cleared.
if [[ -n "$ARG8" ]]; then
    if [[ "$ARG8" =~ ^(1|true|yes|TRUE|YES)$ ]]; then
        export SKIP_TABLESPACE="$ARG8"
        unset DB_DATA_DIR
    else
        export DB_DATA_DIR="$ARG8"
        unset SKIP_TABLESPACE
        [[ -n "$ARG9" ]] && export SKIP_TABLESPACE="$ARG9"
    fi
fi

echo ""
echo "========================================"
echo "Database setup (Linux/macOS)"
echo "========================================"
echo ""

# Check for psql in PATH
echo "[1/6] Checking PostgreSQL installation..."

if ! command -v psql &> /dev/null; then
    echo "[ERROR] psql (PostgreSQL client) not found in PATH."
    echo "Install PostgreSQL client or add it to PATH, then retry."
    exit 1
fi

echo "Using PGHOST=${PGHOST} PGPORT=${PGPORT} PGUSER=${PGUSER}"

echo "Creating database and user (may ask for postgres password)..."

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
if [[ -z "${DB_PASSWORD:-}" ]]; then
    echo "[ERROR] DB_PASSWORD not set. Provide via .env, environment, or seventh positional argument."
    exit 1
fi
if [[ -z "${PGPASSWORD:-}" ]]; then
    echo "[ERROR] PGPASSWORD not set. Provide via .env, environment, or fourth positional argument."
    exit 1
fi

# Check DB_DATA_DIR vs SKIP_TABLESPACE relationship
if [[ -z "${DB_DATA_DIR:-}" ]] && [[ -z "${SKIP_TABLESPACE:-}" ]]; then
    echo "[ERROR] DB_DATA_DIR not set. Provide via .env, environment, or eighth positional argument."
    exit 1
fi
if [[ -n "${DB_DATA_DIR:-}" ]] && [[ -n "${SKIP_TABLESPACE:-}" ]]; then
    echo "[ERROR] DB_DATA_DIR is set but SKIP_TABLESPACE is also specified; these are mutually exclusive."
    exit 1
fi

# Create database user (ignore if exists)
echo "[3/6] Creating database user (if not exists)..."

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '${DB_USER}') THEN CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}'; END IF; END\$\$;" 2>/dev/null || echo "[WARN] Could not create user (you may need to run as a superuser or provide correct postgres password)"

echo "[4/6] Preparing tablespace directory and tablespace..."
if [[ -n "${SKIP_TABLESPACE:-}" ]]; then
    echo "[INFO] SKIP_TABLESPACE is set; skipping tablespace and directory creation"
else
    # DB_DATA_DIR is required, so create tablespace and database
    DB_FULL_PATH="${DB_DATA_DIR}/${DB_NAME}"
    if [[ ! -d "$DB_FULL_PATH" ]]; then
        echo "Creating directory: $DB_FULL_PATH"
        mkdir -p "$DB_FULL_PATH" || {
            echo "[ERROR] Failed to create directory $DB_FULL_PATH"
            exit 1
        }
    fi

    # Check for existing tablespace
    TS_CHECK=$(psql -U "${PGUSER}" -h "${PGHOST}" -t -c "SELECT 1 FROM pg_tablespace WHERE spcname='stock_data_space';" 2>&1 | tr -d '[:space:]')
    if [[ "$TS_CHECK" != "1" ]]; then
        echo "Creating tablespace stock_data_space at $DB_FULL_PATH"
        psql -U "${PGUSER}" -h "${PGHOST}" -c "CREATE TABLESPACE stock_data_space OWNER ${PGUSER} LOCATION '$DB_FULL_PATH';" 2>/dev/null || echo "[WARN] Failed to create tablespace (it may already exist or you may lack privileges)"
    else
        echo "Tablespace stock_data_space already exists"
    fi
fi

# Check if the database exists; if not, create it
echo "[5/6] Creating database if not exists..."

DB_EXISTS=$(psql -U "${PGUSER}" -h "${PGHOST}" -t -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" 2>&1 | tr -d '[:space:]')
if [[ "$DB_EXISTS" != "1" ]]; then
    if [[ -n "${SKIP_TABLESPACE:-}" ]]; then
        # Create database without tablespace (use default)
        psql -U "${PGUSER}" -h "${PGHOST}" -c "CREATE DATABASE ${DB_NAME} WITH OWNER = ${PGUSER} ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TEMPLATE = template0 CONNECTION LIMIT = -1;" 2>/dev/null || {
            echo "[ERROR] Failed to create database"
            exit 1
        }
    else
        # Create database with custom tablespace
        psql -U "${PGUSER}" -h "${PGHOST}" -c "CREATE DATABASE ${DB_NAME} WITH OWNER = ${PGUSER} ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TABLESPACE = stock_data_space TEMPLATE = template0 CONNECTION LIMIT = -1;" 2>/dev/null || {
            echo "[ERROR] Failed to create database"
            exit 1
        }
    fi
else
    echo "Database ${DB_NAME} already exists"
fi

# Grant privileges
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" 2>/dev/null || echo "[WARN] Could not grant privileges"

# Apply initial schema if present
echo "[6/6] Applying initial schema (if present) and finishing..."

if [[ -f "$STOCK_SQL" ]]; then
    echo "Applying stock tables schema: $STOCK_SQL"
    psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -f "$STOCK_SQL" || echo "[WARN] Failed to apply $STOCK_SQL (check SQL file and permissions)"
else
    echo "[WARN] $STOCK_SQL not found; skipping stock tables apply"
fi

if [[ -f "$MGMT_SQL" ]]; then
    echo "Applying management tables schema: $MGMT_SQL"
    psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -f "$MGMT_SQL" || echo "[WARN] Failed to apply $MGMT_SQL (check SQL file and permissions)"
else
    echo "[WARN] $MGMT_SQL not found; skipping management tables apply"
fi

echo ""
echo "[SUCCESS] Database setup script finished."
exit 0
