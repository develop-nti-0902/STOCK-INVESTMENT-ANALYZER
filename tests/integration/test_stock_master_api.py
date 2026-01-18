"""銘柄マスタAPI統合テスト

httpx.AsyncClientを使って実際のAPIエンドポイントを呼び出し、
DBへの格納まで含めて動作確認を行う統合テスト
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.stock_master import StockMaster

pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
async def test_db_setup(monkeypatch):
    """テスト用のDBエンジンとセッションメーカーをセットアップ"""
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"Skipping integration test: missing DB config ({exc})")

    engine = create_async_engine(DATABASE_URL, echo=False)

    # モジュールの get_engine をテスト用エンジンに差し替える
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    # キャッシュクリア
    try:
        db_mod.get_session_maker.cache_clear()
    except Exception:
        pass
    try:
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    # テーブル作成とクリーンアップ
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(delete(StockMaster))

    yield engine

    # テスト後のクリーンアップ
    async with engine.begin() as conn:
        await conn.execute(delete(StockMaster))
    await engine.dispose()


@pytest.mark.anyio
async def test_stock_master_refresh_api(test_db_setup):
    """POST /api/v1/stock-master/refresh のテスト

    銘柄マスタ更新APIを呼び出し、DBに実際にデータが格納されることを確認
    """
    # Arrange & Act: AsyncClientを使ってAPIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/stock-master/refresh",
            params={"batch_size": 100},
        )

    # Assert: レスポンスの検証
    assert response.status_code == 200
    json_data = response.json()
    assert "message" in json_data
    assert "updated_count" in json_data
    assert json_data["updated_count"] > 0

    updated_count = json_data["updated_count"]

    # Assert: DBに実際にデータが格納されていることを確認
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        result = await session.execute(select(StockMaster))
        rows = result.scalars().all()

        # 更新件数とDB格納件数が一致することを確認
        assert len(rows) == updated_count
        assert len(rows) > 0

        # サンプルデータの検証
        first_row = rows[0]
        assert first_row.stock_code is not None
        assert first_row.stock_name is not None


@pytest.mark.anyio
async def test_stock_master_get_symbols_api(test_db_setup):
    """GET /api/v1/stock-master/symbols のテスト

    全銘柄コード取得APIを呼び出し、格納済みデータが取得できることを確認
    """
    # Arrange: まずデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # テストデータを作成（正しいフィールド名を使用）
        test_stocks = [
            StockMaster(
                stock_code="1301",
                stock_name="極洋",
                market_category="プライム",
                sector_name_33="水産・農林業",
                is_active=1,
            ),
            StockMaster(
                stock_code="1305",
                stock_name="ダイワボウホールディングス",
                market_category="プライム",
                sector_name_33="繊維製品",
                is_active=1,
            ),
            StockMaster(
                stock_code="1332",
                stock_name="日本水産",
                market_category="プライム",
                sector_name_33="水産・農林業",
                is_active=0,  # 非アクティブ
            ),
        ]
        session.add_all(test_stocks)
        await session.commit()

    # Act: symbols エンドポイントを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-master/symbols")

    # Assert: レスポンスの検証
    assert response.status_code == 200
    json_data = response.json()
    assert "symbols" in json_data
    assert "count" in json_data

    # アクティブな銘柄のみが返される（2件）
    assert json_data["count"] == 2
    assert len(json_data["symbols"]) == 2
    assert "1301" in json_data["symbols"]
    assert "1305" in json_data["symbols"]
    assert "1332" not in json_data["symbols"]  # 非アクティブは含まれない


@pytest.mark.anyio
async def test_stock_master_get_symbols_by_market_api(test_db_setup):
    """GET /api/v1/stock-master/symbols/market/{market} のテスト

    市場別銘柄コード取得APIを呼び出し、フィルタリングされたデータが取得できることを確認
    """
    # Arrange: テストデータを作成
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        test_stocks = [
            StockMaster(
                stock_code="1301",
                stock_name="極洋",
                market_category="プライム",
                sector_name_33="水産・農林業",
                is_active=1,
            ),
            StockMaster(
                stock_code="1305",
                stock_name="ダイワボウホールディングス",
                market_category="プライム",
                sector_name_33="繊維製品",
                is_active=1,
            ),
            StockMaster(
                stock_code="1417",
                stock_name="ミライト・ワン",
                market_category="スタンダード",
                sector_name_33="建設業",
                is_active=1,
            ),
            StockMaster(
                stock_code="1435",
                stock_name="TATERU",
                market_category="グロース",
                sector_name_33="建設業",
                is_active=1,
            ),
        ]
        session.add_all(test_stocks)
        await session.commit()

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        # Act & Assert: プライム市場の銘柄を取得
        response = await client.get(
            "/api/v1/stock-master/symbols/market/プライム"
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["count"] == 2
        assert "1301" in json_data["symbols"]
        assert "1305" in json_data["symbols"]
        assert "1417" not in json_data["symbols"]
        assert "1435" not in json_data["symbols"]

        # Act & Assert: スタンダード市場の銘柄を取得
        response = await client.get(
            "/api/v1/stock-master/symbols/market/スタンダード"
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["count"] == 1
        assert "1417" in json_data["symbols"]

        # Act & Assert: 存在しない市場の場合は404
        response = await client.get(
            "/api/v1/stock-master/symbols/market/存在しない市場"
        )

        assert response.status_code == 404
        json_data = response.json()
        # カスタムエラーハンドラーの形式に対応
        assert "error" in json_data
        assert "message" in json_data["error"]


@pytest.mark.anyio
async def test_stock_master_get_symbols_empty_db(test_db_setup):
    """GET /api/v1/stock-master/symbols の空DB時のテスト"""
    # Arrange: DBは空の状態（test_db_setupでクリーンアップ済み）

    # Act: symbols エンドポイントを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-master/symbols")

    # Assert: 空のリストが返される
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["count"] == 0
    assert json_data["symbols"] == []


@pytest.mark.anyio
async def test_stock_master_reset_api(test_db_setup):
    """DELETE /api/v1/stock-master/reset のテスト

    銘柄マスタリセットAPIを呼び出し、DBのデータが全削除されることを確認
    """
    # Arrange: まずデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        test_stocks = [
            StockMaster(
                stock_code="1301",
                stock_name="極洋",
                market_category="プライム",
                sector_name_33="水産・農林業",
                is_active=1,
            ),
            StockMaster(
                stock_code="1305",
                stock_name="ダイワボウホールディングス",
                market_category="プライム",
                sector_name_33="繊維製品",
                is_active=1,
            ),
            StockMaster(
                stock_code="1417",
                stock_name="ミライト・ワン",
                market_category="スタンダード",
                sector_name_33="建設業",
                is_active=1,
            ),
        ]
        session.add_all(test_stocks)
        await session.commit()

    # Assert: データが格納されていることを確認
    async with session_maker() as session:
        result = await session.execute(select(StockMaster))
        rows = result.scalars().all()
        assert len(rows) == 3

    # Act: リセットAPIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.delete("/api/v1/stock-master/reset")

    # Assert: レスポンスの検証
    assert response.status_code == 200
    json_data = response.json()
    assert "message" in json_data
    assert "deleted_count" in json_data
    assert json_data["deleted_count"] == 3

    # Assert: DBからデータが削除されていることを確認
    async with session_maker() as session:
        result = await session.execute(select(StockMaster))
        rows = result.scalars().all()
        assert len(rows) == 0
