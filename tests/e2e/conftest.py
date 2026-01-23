import os
import socket

import pytest
from fastapi.testclient import TestClient

from app.main import app


def is_db_reachable() -> bool:
    # asyncpg を使った DB 接続チェックはイベントループの競合を起こす
    # ため、ここでは同期ソケット接続で到達性を確認する。
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
    if not is_db_reachable():
        skip_marker = pytest.mark.skip(
            reason="DB unreachable — skipping E2E tests"
        )
        for item in items:
            # ファイルパスをUNIX形式に変換して判定
            if "tests/e2e" in str(item.fspath).replace("\\", "/"):
                item.add_marker(skip_marker)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
