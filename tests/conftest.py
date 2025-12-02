from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.utils.database import get_db as real_get_db


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
    """

    # outer-scope 名と重複しないよう、request からフィクスチャ値を取得する
    # モジュールスコープのフィクスチャ名を上書きしないようにローカル名を変更する
    mock_session = request.getfixturevalue("mock_db_session")

    async def _override_get_db():
        yield mock_session

    try:
        with TestClient(fastapi_app) as tc:
            yield tc
    finally:
        # テスト終了後にオーバーライドを削除してクリーンアップ
        fastapi_app.dependency_overrides.pop(real_get_db, None)
