"""統合テスト用の共通フィクスチャ。

DBを使用する統合テストでは、各テストごとにデータベースエンジンの
キャッシュをクリアしてイベントループの不一致エラーを回避する。
"""

import pytest_asyncio

from app.utils.database import close_db, get_engine, get_session_maker


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_db_engine_cache():
    """各統合テスト前後にDBエンジンキャッシュをクリアする。

    非同期テストでは各テストごとに新しいイベントループが作成されるため、
    キャッシュされたエンジンが古いループに紐付いたままだと
    "got Future attached to a different loop" エラーが発生する。

    このfixtureは:
    1. テスト前にキャッシュをクリアし、新しいループでエンジンを再作成可能にする
    2. テスト後に接続を適切にクリーンアップする

    `autouse=True` により、tests/integration/ 配下の全テストで自動実行される。
    """
    # テスト前: キャッシュをクリアして新しいイベントループでエンジンを再作成
    get_session_maker.cache_clear()
    get_engine.cache_clear()

    yield

    # テスト後: 接続をクリーンアップ
    try:
        await close_db()
    except Exception:
        # エンジンが作成されていない場合もあるのでエラーは無視
        pass
