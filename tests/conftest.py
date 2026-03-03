"""Test fixtures and helpers for the test suite.

共通の pytest フィクスチャを定義します。
"""

# flake8: noqa

import asyncio
import gc
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.utils.database import close_db
from app.utils.database import get_db as real_get_db


def _is_e2e_test_item(item: pytest.Item) -> bool:
    path = getattr(item, "path", None)
    if path is None:
        path = Path(str(item.fspath))
    path_str = str(path).replace("\\", "/")
    return "/tests/e2e/" in path_str


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if not _is_e2e_test_item(item):
            continue

        item.add_marker(pytest.mark.e2e)
        item.add_marker(pytest.mark.xdist_group("e2e"))


@pytest.fixture(scope="function", autouse=True)
def reset_event_loop():
    """各テストの前後でイベントループを適切に管理する.

    autouser=True により、すべてのテストで自動的に実行される。
    """
    # テスト前: 既存のループをクリーンアップし、データベースエンジンをリセット
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            # 閉じられたループがある場合は新しいループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # ループが存在しない場合は新しいループを作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 前のテストのデータベースエンジンをクリーンアップ
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.run_until_complete(close_db())
    except Exception:
        pass

    yield

    # テスト後: データベースエンジンをクリーンアップしてリソースを解放
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.run_until_complete(close_db())
    except Exception:
        pass

    # テスト後: リソースをクリーンアップ（ループは閉じない）
    try:
        gc.collect()
    except Exception:
        pass


@pytest.fixture(scope="function")
def mock_db_session():
    """テスト用の簡易な非同期 DB セッションモック（AsyncMock）を返します。

    DB への副作用を避けるために、テスト内で DB 操作をモック化する際に使用します。
    将来的に依存のオーバーライドを追加する場合はここで拡張してください。
    """
    return AsyncMock()


@pytest.fixture(scope="function")
def client(request):
    """モックセッションで `get_db` をオーバーライドした `TestClient` を提供します。

    pytest の fixture 注入による名前のシャドーイングを避けるため、
    `request.getfixturevalue` で `mock_db_session` を取得します。

    E2Eテストの場合は実際のDB接続を使用します。
    """

    # outer-scope 名と重複しないよう、request からフィクスチャ値を取得する
    # モジュールスコープのフィクスチャ名を上書きしないようにローカル名を変更する

    # E2Eテストかどうかを判定
    is_e2e = _is_e2e_test_item(request.node)

    if not is_e2e:
        # ユニットテストの場合: モックセッションを使用
        mock_session = request.getfixturevalue("mock_db_session")

        async def _override_get_db():
            yield mock_session

        # DBオーバーライドを設定
        fastapi_app.dependency_overrides[real_get_db] = _override_get_db

        try:
            with TestClient(fastapi_app) as tc:
                yield tc
        finally:
            # テスト終了後にオーバーライドを削除してクリーンアップ
            fastapi_app.dependency_overrides.pop(real_get_db, None)

            # リソースのクリーンアップ
            # ガベージコレクションを実行して未処理のリソースをクリーンアップ
            gc.collect()

            # SQLAlchemy のコネクションプールをクリーンアップ
            # これにより、古いイベントループへの参照が残らないようにする
            try:
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    gc.collect()
            except Exception:
                pass
    else:
        # E2Eテストの場合: 実際のDB接続を使用（オーバーライドなし）
        try:
            with TestClient(fastapi_app) as tc:
                yield tc
        finally:
            # リソースのクリーンアップ
            gc.collect()
