"""株価データAPI統合テスト

httpx.AsyncClientを使って実際のAPIエンドポイントを呼び出し、
DBからのデータ取得を確認する統合テスト
"""

from datetime import datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.stock_data import Stocks1d, Stocks1h, Stocks1m
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
        await conn.execute(delete(Stocks1m))
        await conn.execute(delete(Stocks1h))
        await conn.execute(delete(Stocks1d))
        await conn.execute(delete(StockMaster))

    yield engine

    # テスト後のクリーンアップ
    async with engine.begin() as conn:
        await conn.execute(delete(Stocks1m))
        await conn.execute(delete(Stocks1h))
        await conn.execute(delete(Stocks1d))
        await conn.execute(delete(StockMaster))
    await engine.dispose()


@pytest.mark.anyio
async def test_get_stock_price_1d_api(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/1d のテスト

    日足データ取得APIを呼び出し、DBからデータが取得できることを確認
    """
    # Arrange: テストデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # stock_masterに銘柄を登録
        stock_master = StockMaster(
            stock_code="7203",
            stock_name="テスト銘柄",
            market_category="プライム",
            sector_name_33="輸送用機器",
            is_active=1,
        )
        session.add(stock_master)
        await session.flush()

        test_data = [
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, 0, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1100.00"),
                low=Decimal("990.00"),
                close=Decimal("1050.00"),
                adj_close=Decimal("1050.00"),
                volume=1000000,
            ),
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, 11, 0, 0, 0),
                open=Decimal("1050.00"),
                high=Decimal("1150.00"),
                low=Decimal("1040.00"),
                close=Decimal("1100.00"),
                adj_close=Decimal("1100.00"),
                volume=1200000,
            ),
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, 12, 0, 0, 0),
                open=Decimal("1100.00"),
                high=Decimal("1200.00"),
                low=Decimal("1090.00"),
                close=Decimal("1150.00"),
                adj_close=Decimal("1150.00"),
                volume=1500000,
            ),
        ]
        session.add_all(test_data)
        await session.commit()

    # Act: APIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-price/7203/1d")

    # Assert: レスポンスの検証
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["symbol"] == "7203"
    assert json_data["timeframe"] == "1d"
    assert json_data["count"] == 3
    assert len(json_data["data"]) == 3

    # 最新データ（降順）が最初に来る
    first_item = json_data["data"][0]
    assert first_item["symbol"] == "7203"
    assert first_item["close"] == 1150.0
    assert first_item["volume"] == 1500000


@pytest.mark.anyio
async def test_get_stock_price_with_date_range(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/1d with date range のテスト

    期間指定でデータを取得できることを確認
    """
    # Arrange: テストデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # stock_masterに銘柄を登録
        stock_master = StockMaster(
            stock_code="7203",
            stock_name="テスト銘柄",
            market_category="プライム",
            sector_name_33="輸送用機器",
            is_active=1,
        )
        session.add(stock_master)
        await session.flush()

        test_data = [
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, 0, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1100.00"),
                low=Decimal("990.00"),
                close=Decimal("1050.00"),
                adj_close=Decimal("1050.00"),
                volume=1000000,
            ),
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, 15, 0, 0, 0),
                open=Decimal("1050.00"),
                high=Decimal("1150.00"),
                low=Decimal("1040.00"),
                close=Decimal("1100.00"),
                adj_close=Decimal("1100.00"),
                volume=1200000,
            ),
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, 20, 0, 0, 0),
                open=Decimal("1100.00"),
                high=Decimal("1200.00"),
                low=Decimal("1090.00"),
                close=Decimal("1150.00"),
                adj_close=Decimal("1150.00"),
                volume=1500000,
            ),
        ]
        session.add_all(test_data)
        await session.commit()

    # Act: 期間を指定してAPIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/stock-price/7203/1d",
            params={"start": "2024-01-12", "end": "2024-01-18"},
        )

    # Assert: 期間内のデータのみ取得される
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["count"] == 1
    assert len(json_data["data"]) == 1
    # timestampは2024-01-15が含まれていることを確認（タイムゾーン付きなので柔軟に判定）
    timestamp_str = json_data["data"][0]["timestamp"]
    assert "2024-01-15" in timestamp_str or "2024-01-14" in timestamp_str


@pytest.mark.anyio
async def test_get_stock_price_1h_api(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/1h のテスト

    時間足データ取得APIを呼び出し、DBからデータが取得できることを確認
    """
    # Arrange: テストデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # stock_masterに銘柄を登録
        stock_master = StockMaster(
            stock_code="7203",
            stock_name="テスト銘柄",
            market_category="プライム",
            sector_name_33="輸送用機器",
            is_active=1,
        )
        session.add(stock_master)
        await session.flush()

        test_data = [
            Stocks1h(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, 9, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1020.00"),
                low=Decimal("990.00"),
                close=Decimal("1010.00"),
                adj_close=Decimal("1010.00"),
                volume=100000,
            ),
            Stocks1h(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, 10, 0, 0),
                open=Decimal("1010.00"),
                high=Decimal("1030.00"),
                low=Decimal("1000.00"),
                close=Decimal("1020.00"),
                adj_close=Decimal("1020.00"),
                volume=120000,
            ),
        ]
        session.add_all(test_data)
        await session.commit()

    # Act: APIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-price/7203/1h")

    # Assert: レスポンスの検証
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["symbol"] == "7203"
    assert json_data["timeframe"] == "1h"
    assert json_data["count"] == 2
    assert len(json_data["data"]) == 2


@pytest.mark.anyio
async def test_get_stock_price_1m_api(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/1m のテスト

    分足データ取得APIを呼び出し、DBからデータが取得できることを確認
    """
    # Arrange: テストデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # stock_masterに銘柄を登録
        stock_master = StockMaster(
            stock_code="7203",
            stock_name="テスト銘柄",
            market_category="プライム",
            sector_name_33="輸送用機器",
            is_active=1,
        )
        session.add(stock_master)
        await session.flush()

        test_data = [
            Stocks1m(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, 9, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1005.00"),
                low=Decimal("999.00"),
                close=Decimal("1002.00"),
                adj_close=Decimal("1002.00"),
                volume=10000,
            ),
            Stocks1m(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, 9, 1, 0),
                open=Decimal("1002.00"),
                high=Decimal("1008.00"),
                low=Decimal("1001.00"),
                close=Decimal("1005.00"),
                adj_close=Decimal("1005.00"),
                volume=12000,
            ),
        ]
        session.add_all(test_data)
        await session.commit()

    # Act: APIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-price/7203/1m")

    # Assert: レスポンスの検証
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["symbol"] == "7203"
    assert json_data["timeframe"] == "1m"
    assert json_data["count"] == 2


@pytest.mark.anyio
async def test_get_stock_price_not_found(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/1d の404テスト

    データが存在しない銘柄の場合、404が返ることを確認
    """
    # Act: 存在しない銘柄でAPIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-price/9999/1d")

    # Assert: 404が返される
    assert response.status_code == 404
    json_data = response.json()
    assert "error" in json_data
    assert "message" in json_data["error"]


@pytest.mark.anyio
async def test_get_stock_price_invalid_timeframe(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/{timeframe} の無効な時間軸テスト

    無効な時間軸を指定した場合、400または422が返ることを確認
    """
    # Act: 無効な時間軸でAPIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/stock-price/7203/invalid")

    # Assert: 400または422（バリデーションエラー）が返される
    assert response.status_code in [400, 422]


@pytest.mark.anyio
async def test_get_stock_price_with_limit_and_offset(test_db_setup):
    """GET /api/v1/stock-price/{symbol}/1d with limit and offset のテスト

    limitとoffsetパラメータが正しく動作することを確認
    """
    # Arrange: テストデータをDBに格納（5件）
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # stock_masterに銘柄を登録
        stock_master = StockMaster(
            stock_code="7203",
            stock_name="テスト銘柄",
            market_category="プライム",
            sector_name_33="輸送用機器",
            is_active=1,
        )
        session.add(stock_master)
        await session.flush()

        test_data = [
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, day, 0, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1100.00"),
                low=Decimal("990.00"),
                close=Decimal("1050.00"),
                adj_close=Decimal("1050.00"),
                volume=1000000,
            )
            for day in range(10, 15)
        ]
        session.add_all(test_data)
        await session.commit()

    # Act: limit=2, offset=1でAPIを呼び出す
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/stock-price/7203/1d", params={"limit": 2, "offset": 1}
        )

    # Assert: 2件のデータが返される（2番目と3番目）
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["count"] == 2
    assert len(json_data["data"]) == 2


@pytest.mark.anyio
async def test_delete_all_stock_price_data_api(test_db_setup):
    """DELETE /api/v1/stock-price/{timeframe}/all のテスト

    指定時間軸の全データ削除APIを呼び出し、全レコードが削除されることを確認
    """
    # Arrange: テストデータをDBに格納
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        # stock_masterに銘柄を登録
        stock_master_1 = StockMaster(
            stock_code="7203",
            stock_name="テスト銘柄1",
            market_category="プライム",
            sector_name_33="輸送用機器",
            is_active=1,
        )
        stock_master_2 = StockMaster(
            stock_code="9984",
            stock_name="テスト銘柄2",
            market_category="プライム",
            sector_name_33="情報・通信業",
            is_active=1,
        )
        session.add_all([stock_master_1, stock_master_2])
        await session.flush()

        # 1d, 1h, 1mのテストデータを追加
        test_data_1d = [
            Stocks1d(
                symbol="7203",
                timestamp=datetime(2024, 1, day, 0, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1100.00"),
                low=Decimal("990.00"),
                close=Decimal("1050.00"),
                adj_close=Decimal("1050.00"),
                volume=1000000,
            )
            for day in range(10, 15)
        ]
        test_data_1d.extend(
            [
                Stocks1d(
                    symbol="9984",
                    timestamp=datetime(2024, 1, day, 0, 0, 0),
                    open=Decimal("2000.00"),
                    high=Decimal("2100.00"),
                    low=Decimal("1990.00"),
                    close=Decimal("2050.00"),
                    adj_close=Decimal("2050.00"),
                    volume=2000000,
                )
                for day in range(10, 13)
            ]
        )
        session.add_all(test_data_1d)

        test_data_1h = [
            Stocks1h(
                symbol="7203",
                timestamp=datetime(2024, 1, 10, hour, 0, 0),
                open=Decimal("1000.00"),
                high=Decimal("1100.00"),
                low=Decimal("990.00"),
                close=Decimal("1050.00"),
                adj_close=Decimal("1050.00"),
                volume=100000,
            )
            for hour in range(9, 15)
        ]
        session.add_all(test_data_1h)
        await session.commit()

    # 削除前のデータ件数を確認
    async with session_maker() as session:
        from sqlalchemy import select

        count_1d = (await session.execute(select(Stocks1d))).scalars().all()
        count_1h = (await session.execute(select(Stocks1h))).scalars().all()

        assert len(count_1d) == 8  # 7203: 5件 + 9984: 3件
        assert len(count_1h) == 6  # 7203: 6件

    # Act: 1dテーブルの全データを削除
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.delete("/api/v1/stock-price/1d/all")

    # Assert: 削除レスポンスを確認
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["timeframe"] == "1d"
    assert json_data["deleted_count"] == 8
    assert "deleted" in json_data["message"].lower()

    # 削除後のデータ件数を確認（1dは0件、1hは残っている）
    async with session_maker() as session:
        count_1d_after = (
            (await session.execute(select(Stocks1d))).scalars().all()
        )
        count_1h_after = (
            (await session.execute(select(Stocks1h))).scalars().all()
        )

        assert len(count_1d_after) == 0  # 全削除
        assert len(count_1h_after) == 6  # 1hは影響なし


@pytest.mark.anyio
async def test_delete_all_empty_table_api(test_db_setup):
    """DELETE /api/v1/stock-price/{timeframe}/all のテスト（空テーブル）

    データが存在しないテーブルに対して削除APIを実行しても正常動作することを確認
    """
    # Arrange: データなし（test_db_setupで既にクリーンアップ済み）

    # Act: 1mテーブルの全データを削除（空テーブル）
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.delete("/api/v1/stock-price/1m/all")

    # Assert: 正常にレスポンスが返ることを確認
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["timeframe"] == "1m"
    assert json_data["deleted_count"] == 0
    assert "deleted" in json_data["message"].lower()


@pytest.mark.anyio
async def test_delete_all_invalid_timeframe_api(test_db_setup):
    """DELETE /api/v1/stock-price/{timeframe}/all のテスト（無効な時間軸）

    無効な時間軸を指定した場合にエラーが返ることを確認
    """
    # Act: 無効な時間軸で削除APIを実行
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.delete("/api/v1/stock-price/invalid/all")

    # Assert: バリデーションエラー（400 or 422）
    assert response.status_code in (400, 422)
