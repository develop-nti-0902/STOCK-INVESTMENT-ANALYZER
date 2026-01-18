#!/usr/bin/env bash
# =============================================================================
# Alembic マイグレーション適用スクリプト (Linux/Mac)
# Location: scripts/databaseSetup/migrate.sh
#
# このスクリプトは既存のデータベースに対してAlembicマイグレーションを適用します。
# データベースを破棄せずにスキーマ変更（テーブル追加、カラム変更など）を行います。
#
# 使用例:
#   ./migrate.sh              # 最新バージョンまでマイグレーション
#   ./migrate.sh +1           # 1つ先のバージョンにマイグレーション
#   ./migrate.sh -1           # 1つ前のバージョンにダウングレード
#   ./migrate.sh 4e581533f2e4 # 特定のリビジョンにマイグレーション
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# マイグレーションターゲット（デフォルトはhead）
MIGRATION_TARGET="${1:-head}"

echo ""
echo "========================================"
echo "Alembic Migration Tool"
echo "========================================"
echo ""

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
echo ""

# 現在のマイグレーション状態を表示
echo "[Current migration status]"
"${PYTHON_CMD}" -m alembic current || {
    echo "[ERROR] Failed to get current migration status"
    echo "Please check:"
    echo "  - Database is running and accessible"
    echo "  - Connection settings in .env"
    echo "  - Alembic is installed: ${PYTHON_CMD} -m pip install alembic"
    exit 1
}

echo ""
echo "[Available migrations]"
"${PYTHON_CMD}" -m alembic history --verbose
echo ""

# ユーザー確認
if [[ "${MIGRATION_TARGET}" == "head" ]]; then
    echo "About to migrate to: LATEST VERSION (head)"
else
    echo "About to migrate to: ${MIGRATION_TARGET}"
fi

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

echo ""
echo "[Applying migration]"

# ダウングレード判定（-1などの場合）
if [[ "${MIGRATION_TARGET}" =~ ^-[0-9] ]]; then
    echo "Downgrading..."
    "${PYTHON_CMD}" -m alembic downgrade "${MIGRATION_TARGET}"
else
    echo "Upgrading..."
    "${PYTHON_CMD}" -m alembic upgrade "${MIGRATION_TARGET}"
fi

if [[ $? -ne 0 ]]; then
    echo ""
    echo "[ERROR] Migration failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check error message above"
    echo "  2. Verify database connection"
    echo "  3. Check migration file syntax"
    echo "  4. Review alembic/env.py configuration"
    echo ""
    echo "Useful commands:"
    echo "  ${PYTHON_CMD} -m alembic current    # Show current version"
    echo "  ${PYTHON_CMD} -m alembic history    # Show migration history"
    echo "  ${PYTHON_CMD} -m alembic stamp head # Mark as up-to-date without running"
    echo ""
    exit 1
fi

echo ""
echo "[New migration status]"
"${PYTHON_CMD}" -m alembic current

echo ""
echo "========================================"
echo "[SUCCESS] Migration completed!"
echo "========================================"
echo ""

exit 0
