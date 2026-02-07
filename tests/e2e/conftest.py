"""E2E テスト用の共通フィクスチャとユーティリティ.

このモジュールは E2E テストの共通セットアップを提供します.
"""

import os
import socket

import pytest
from fastapi.testclient import TestClient

from app.main import app


def is_db_reachable() -> bool:
    """DB 到達性を同期ソケットで簡易チェックする.

    asyncpg を使った接続チェックはイベントループに影響するため、
    E2E 実行前の到達性確認は同期ソケットで行う.
    """
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    # 優先: アプリ設定から取得（.env や環境変数を参照した結果）
    try:
        from app.utils.config import get_settings

        try:
            settings = get_settings()
            host = getattr(settings, "DB_HOST", host)
            port = getattr(settings, "DB_PORT", port)
        except Exception:
            # 設定が不完全な場合は環境変数にフォールバック
            pass
    except Exception:
        # import エラー等は無視して環境変数を使う
        pass
    if not host or not port:
        return False
    try:
        with socket.create_connection((host, int(port)), timeout=1):
            return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """E2E テスト実行時に DB 到達不良なら該当テストをスキップする."""
    if not is_db_reachable():
        skip_marker = pytest.mark.skip(reason="DB unreachable — skipping E2E tests")
        for item in items:
            # ファイルパスをUNIX形式に変換して判定
            if "tests/e2e" in str(item.fspath).replace("\\", "/"):
                item.add_marker(skip_marker)


@pytest.fixture(scope="module")
def client():
    """FastAPI `TestClient` を提供する pytest fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function", autouse=True)
def clear_advisory_locks():
    """各テスト実行前にPostgreSQLのadvisory lockをクリアする.

    latest_stocks_1d のリフレッシュジョブで使用されるadvisory lockが
    前のテスト実行から残っている場合にクリアします。
    """
    from sqlalchemy import text

    from app.utils.database import get_engine

    try:
        engine = get_engine()
        # すべてのadvisory lockを解放（現在のセッションで保持しているもの）
        with engine.sync_engine.connect() as conn:
            # このセッションが保持しているすべてのadvisory lockを解放
            conn.execute(text("SELECT pg_advisory_unlock_all()"))
            conn.commit()
    except Exception:
        # ロック解放に失敗してもテストは続行
        pass

    yield

    # テスト終了後にもクリーンアップ
    try:
        engine = get_engine()
        with engine.sync_engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_unlock_all()"))
            conn.commit()
    except Exception:
        pass
