#!/usr/bin/env bash
# =============================================================================
# Alembic対応 PostgreSQL データベース初期セットアップスクリプト (Linux/Mac)
# Location: scripts/databaseSetup/setup_db_alembic.sh
#
# このスクリプトは以下を実行します:
#   1. データベースユーザーの作成
#   2. テーブルスペースの作成（データ配置ディレクトリ指定）
#   3. データベースの作成
#   4. 権限の付与
#   5. Alembicマイグレーションの適用（テーブル作成）
#
# 注意: 既存のデータベースを破棄せずにスキーマ変更する場合は migrate.sh を使用してください
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# .envファイルから環境変数を読み込み
if [[ -f "${REPO_ROOT}/.env" ]]; then
    echo "[INFO] Loading environment variables from ${REPO_ROOT}/.env"
    export $(grep -v '^#' "${REPO_ROOT}/.env" | xargs)
fi

echo ""
echo "========================================"
echo "Alembic Database Setup (Linux/Mac)"
echo "========================================"
echo ""

# 必須変数の検証
echo "[1/6] Validating required variables..."

: "${PGHOST:?PGHOST not set}"
: "${PGPORT:?PGPORT not set}"
: "${PGUSER:?PGUSER not set}"
: "${PGPASSWORD:?PGPASSWORD not set}"
: "${DB_NAME:?DB_NAME not set}"
: "${DB_USER:?DB_USER not set}"
: "${DB_PASSWORD:?DB_PASSWORD not set}"
: "${DB_DATA_DIR:?DB_DATA_DIR not set}"

export PGPASSWORD

echo "Using PGHOST=${PGHOST} PGPORT=${PGPORT} PGUSER=${PGUSER}"
echo "Database: ${DB_NAME}"
echo "Data Directory: ${DB_DATA_DIR}"

# データベースユーザーの作成
echo "[2/6] Creating database user..."

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '${DB_USER}') THEN CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}'; END IF; END\$\$;" 2>/dev/null || {
    echo "[WARN] Could not create user (may already exist or need superuser privileges)"
}

echo "User ${DB_USER} created or already exists"

# テーブルスペース用ディレクトリの作成
echo "[3/6] Preparing tablespace directory..."

DB_FULL_PATH="${DB_DATA_DIR}/${DB_NAME}"
if [[ ! -d "${DB_FULL_PATH}" ]]; then
    echo "Creating directory: ${DB_FULL_PATH}"
    mkdir -p "${DB_FULL_PATH}"
else
    echo "Directory already exists: ${DB_FULL_PATH}"
fi

# テーブルスペースの作成
echo "[4/6] Creating tablespace..."

TABLESPACE_NAME="stock_data_space_${DB_NAME}"

TS_CHECK=$(psql -U "${PGUSER}" -h "${PGHOST}" -t -c "SELECT 1 FROM pg_tablespace WHERE spcname='${TABLESPACE_NAME}';" 2>/dev/null | tr -d ' ')

if [[ "${TS_CHECK}" != "1" ]]; then
    echo "Creating tablespace ${TABLESPACE_NAME} at ${DB_FULL_PATH}"
    psql -U "${PGUSER}" -h "${PGHOST}" -c "CREATE TABLESPACE ${TABLESPACE_NAME} OWNER ${PGUSER} LOCATION '${DB_FULL_PATH}';"
    echo "Tablespace created successfully"
else
    echo "Tablespace ${TABLESPACE_NAME} already exists"
fi

# データベースの作成
echo "[5/6] Creating database..."

DB_EXISTS=$(psql -U "${PGUSER}" -h "${PGHOST}" -t -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" 2>/dev/null | tr -d ' ')

if [[ "${DB_EXISTS}" != "1" ]]; then
    echo "Creating database ${DB_NAME} with tablespace ${TABLESPACE_NAME}"
    psql -U "${PGUSER}" -h "${PGHOST}" -c "CREATE DATABASE ${DB_NAME} WITH OWNER = ${PGUSER} ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TABLESPACE = ${TABLESPACE_NAME} TEMPLATE = template0 CONNECTION LIMIT = -1;"
    echo "Database created successfully"
else
    echo "Database ${DB_NAME} already exists"
fi

# 権限の付与
echo "Granting privileges..."

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" 2>/dev/null || true
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO ${DB_USER};" 2>/dev/null || true
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};" 2>/dev/null || true
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${DB_NAME}" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};" 2>/dev/null || true

echo "Privileges granted successfully"

# Alembicマイグレーションの適用
echo "[6/6] Applying Alembic migrations..."

cd "${REPO_ROOT}"

# Pythonコマンドの検出
if [[ -f ".venv/bin/python" ]]; then
    PYTHON_CMD=".venv/bin/python"
elif [[ -f "venv/bin/python" ]]; then
    PYTHON_CMD="venv/bin/python"
else
    PYTHON_CMD="python3"
fi

echo "Using Python: ${PYTHON_CMD}"
echo "Applying migrations..."

"${PYTHON_CMD}" -m alembic upgrade head || {
    echo "[ERROR] Failed to apply Alembic migrations"
    echo "Please check:"
    echo "  - Alembic is installed: ${PYTHON_CMD} -m pip install alembic"
    echo "  - Database connection settings in .env"
    echo "  - alembic/env.py configuration"
    exit 1
}

echo "Migrations applied successfully"

echo ""
echo "========================================"
echo "[SUCCESS] Database setup completed!"
echo "========================================"
echo ""
echo "Database: ${DB_NAME}"
echo "Tablespace: ${TABLESPACE_NAME}"
echo "Data Location: ${DB_FULL_PATH}"
echo ""
echo "Next steps:"
echo "  - Run tests: pytest"
echo "  - Apply future migrations: scripts/databaseSetup/migrate.sh"
echo "  - Check migration status: ${PYTHON_CMD} -m alembic current"
echo ""

exit 0
