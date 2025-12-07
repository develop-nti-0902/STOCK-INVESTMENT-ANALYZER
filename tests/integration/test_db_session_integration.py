import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod


@pytest.mark.anyio
async def test_engine_warmup_and_get_db(monkeypatch):
    """
    PostgreSQL（asyncpg）を利用して検証します:
    - エンジン生成後に簡単な `SELECT 1` が実行できること
    - `get_db` がセッションを生成し、クエリ実行後にクローズされること

    実行には環境変数 `DATABASE_URL` を指定してください。
    例: postgresql+asyncpg://user:pass@localhost:5432/test_db
    `DATABASE_URL` が設定されていない場合はテストを失敗させます。
    """

    # Arrange: テスト前準備
    # - `app.utils.database.get_database_url()` を利用して接続文字列を取得
    #   （内部で設定の検証が行われ、未設定なら例外が発生するはず）
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:  # pylint: disable=broad-except
        pytest.fail(
            f"Failed to obtain DATABASE URL via get_database_url(): {exc}"
        )

    # Act: テスト対象の操作を実行
    # - 非同期 Postgres エンジンを作成
    engine = create_async_engine(DATABASE_URL, echo=False)

    # - モジュールの get_engine を差し替えて、テスト中はこのエンジンを使わせる
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    # - get_session_maker/get_engine の lru_cache が残っている場合にクリア
    try:
        db_mod.get_session_maker.cache_clear()
    except Exception:
        pass
    try:
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    # Assert: 結果検証
    # - エンジン接続で簡単な SELECT が成功すること
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

    # - get_db() からセッションを取得してクエリ実行できること
    agen = db_mod.get_db()
    session = await agen.__anext__()
    try:
        res = await session.execute(text("SELECT 1"))
        assert res.scalar_one() == 1
    finally:
        # async generator を閉じて commit/close の処理を走らせる
        await agen.aclose()
