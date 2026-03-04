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

    SQLiteの場合はファイルの存在またはメモリDBを確認します。
    E2Eテストは各テスト内で独自のDBセットアップを行うため、
    相対パスの場合は到達可能と判断します。
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
                # sqlite:///path の場合、parsed.path は /path になる（Windows なら /C:/path）
                path = unquote(parsed.path or "")

                # メモリDB の場合
                if path == ":memory:" or path == "" or not path:
                    return True

                # Windows 絶対パスの場合: /C:/path -> C:/path に正規化
                if path.startswith("/") and len(path) > 2 and path[2] == ":":
                    path = path[1:]

                # ファイル存在確認（相対・絶対両方に対応）
                # E2E テストは各テストで独自の DB をセットアップするため、
                # 相対パスの場合は到達可能と判断する
                if os.path.exists(path):
                    return True

                # 相対パスの場合は E2E テスト用として許可
                if not os.path.isabs(path):
                    return True

                # 絶対パスの場合、ファイルが存在しなければ到達不可
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
    """E2E Tests用のイベントループ管理（tests/conftest.py を上書き）.

    tests/conftest.py の `reset_event_loop` を E2E 環境用に上書きします。
    E2E テストでは独自の TestClient を使うため、`close_db()` を呼びません。
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
    """Provide a FastAPI TestClient pytest fixture."""
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
    """No-op for advisory locks in SQLite environment."""
    # SQLite環境では何もせずにyield
    yield


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_database():
    """E2Eテスト用データベースをセットアップ.

    Alembicマイグレーションを実行して、テーブルを作成します。
    セッションスコープで一度だけ実行されます。
    """
    import subprocess
    import sys

    try:
        # alembic upgrade head を実行
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )

        if result.returncode != 0:
            print(f"⚠️  Alembic migration warning: {result.stderr}")
        else:
            print("✅ E2E database initialized with alembic migrations")
    except Exception as e:
        print(f"⚠️  Failed to run alembic migrations: {e}")
        # マイグレーション失敗時も続行（テーブルが既に存在する可能性）

    yield
