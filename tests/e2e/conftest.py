"""E2E テスト用の共通フィクスチャとユーティリティ.

このモジュールは E2E テストの共通セットアップを提供します.
"""

import os
import socket
from urllib.parse import unquote, urlparse

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
        # ホスト/ポートが指定されていない場合は `DATABASE_URL` を確認する
        try:
            # 設定内の `DATABASE_URL` を優先して取得する
            from app.utils.config import get_settings

            settings = get_settings()
            db_url = getattr(settings, "DATABASE_URL", os.getenv("DATABASE_URL"))
        except Exception:
            db_url = os.getenv("DATABASE_URL")

        if db_url:
            parsed = urlparse(db_url)
            scheme = (parsed.scheme or "").lower()
            # SQLite を使う場合、ファイルが存在するかメモリ DB の場合は到達可能と判断する
            if scheme.startswith("sqlite"):
                # Windows では parsed.path が '/C:/path' になることがあるため正規化する
                path = unquote(parsed.path or "")
                if path.startswith("/") and len(path) > 2 and path[2] == ":":
                    path = path[1:]
                if path == ":memory:" or path == "":
                    return True
                return os.path.exists(path)
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


@pytest.fixture(scope="function", autouse=True)
def reset_event_loop_for_e2e():
    """E2E tests用のイベントループ管理（tests/conftest.pyを上書き）.

    tests/conftest.pyのreset_event_loopをE2E環境用に上書きする。
    E2Eテストでは独自のTestClientを使うため、close_db()を呼ばない。
    """
    import asyncio
    import gc

    # テスト前: イベントループの確認/作成
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    yield

    # テスト後: ガベージコレクションのみ
    try:
        gc.collect()
    except Exception:
        pass


@pytest.fixture(scope="function")
def client():
    """FastAPI `TestClient` を提供する pytest fixture."""
    # E2Eテスト環境ではlifespanを無効化（DB接続のハングを防ぐ）
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    @asynccontextmanager
    async def noop_lifespan(_app: FastAPI):
        """テスト用の空のlifespanハンドラ."""
        yield

    # オリジナルのlifespanを保存して、テスト用のlifespanに置き換え
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan

    try:
        with TestClient(app) as c:
            yield c
    finally:
        # テスト後に元のlifespanを復元
        app.router.lifespan_context = original_lifespan


@pytest.fixture(scope="function")
def clear_advisory_locks(request):
    """各E2Eテスト実行前にPostgreSQLのadvisory lockをクリアする.

    latest_stocks_1d のリフレッシュジョブで使用されるadvisory lockが
    前のテスト実行から残っている場合にクリアします。

    Note:
        このフィクスチャはE2Eテストでのみ使用されます。
        データベース接続が不安定な場合はスキップされます。

    Usage:
        テスト関数で明示的に使用するか、E2E専用のautoUseマーカーで自動適用します。
    """
    # E2Eテスト以外ではスキップ
    test_file = str(request.fspath)
    if "tests/e2e" not in test_file.replace("\\", "/"):
        yield
        return

    # DB到達不能な場合はスキップ
    if not is_db_reachable():
        yield
        return

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.utils.database import get_database_url
    from tests.e2e.utils import run_async_safely

    async def _clear_locks():
        """非同期でadvisory lockをクリアする."""
        engine = create_async_engine(get_database_url())
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT pg_advisory_unlock_all()"))
                await conn.commit()
        finally:
            await engine.dispose()

    # テスト前にクリーンアップ
    try:
        run_async_safely(_clear_locks())
    except Exception:
        # ロック解放に失敗してもテストは続行
        pass

    yield

    # テスト終了後にもクリーンアップ
    try:
        run_async_safely(_clear_locks())
    except Exception:
        pass
