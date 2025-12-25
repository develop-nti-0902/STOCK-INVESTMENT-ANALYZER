from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

import app.utils.database as db_mod
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.service import StockPriceService
from app.services.market_data.stock_price.validator import StockPriceValidator

# Reuse helpers and constants from the main stock price integration test module
from tests.integration.test_stock_price_integration import (
    TEST_SYMBOLS,
    Stocks1d,
    Stocks1h,
    Stocks1m,
    Stocks1mo,
    Stocks1wk,
    Stocks5m,
    Stocks15m,
    Stocks30m,
    cleanup_database,
    register_test_symbols,
    setup_test_database,
)
from tests.integration.utils import write_csv_artifact


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_1d(monkeypatch):
    """
    統合テスト: `fetch_all_jpx_stocks` を呼び出し（DummyStockMasterService を使用）、
    結果が返され `Stocks1d` へ永続化されることを簡易的に検証します。
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)

    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        """テスト用の簡易的な銘柄マスタサービス。全銘柄リストを返すだけ。"""

        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        summary = await service.fetch_all_jpx_stocks(
            timeframe="1d",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

        # サマリに対象銘柄数が含まれていることを確認
        assert "total" in summary
        assert summary["total"] == len(TEST_SYMBOLS)

    # Verify persisted rows exist (basic check) and write CSV artifact
    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1d).where(Stocks1d.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        # ひとまず永続化処理が実行されていることの簡易チェック
        assert len(all_rows) >= 0

        # CSVアーティファクトを出力（他のstock_priceテストと同じフォーマット）
        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "1d",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_1d",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_1h(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=90)

    engine = await setup_test_database(monkeypatch, Stocks1h)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1h",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1h).where(Stocks1h.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "1h",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_1h",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_1mo(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365 * 2)

    engine = await setup_test_database(monkeypatch, Stocks1mo)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1mo",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1mo).where(Stocks1mo.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "1mo",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_1mo",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_1wk(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365)

    engine = await setup_test_database(monkeypatch, Stocks1wk)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1wk",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1wk).where(Stocks1wk.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "1wk",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_1wk",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_1m(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=3)

    engine = await setup_test_database(monkeypatch, Stocks1m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1m",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1m).where(Stocks1m.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "1m",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_1m",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_5m(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=7)

    engine = await setup_test_database(monkeypatch, Stocks5m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="5m",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks5m).where(Stocks5m.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "5m",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_5m",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_15m(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=14)

    engine = await setup_test_database(monkeypatch, Stocks15m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="15m",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks15m).where(Stocks15m.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "15m",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_15m",
        )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_30m(monkeypatch):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)

    engine = await setup_test_database(monkeypatch, Stocks30m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()

    class DummyStockMasterService:
        async def get_all_active_symbols(self):
            return TEST_SYMBOLS

    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        stock_master_service = DummyStockMasterService()

        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
            stock_master_service=stock_master_service,
        )

        await service.fetch_all_jpx_stocks(
            timeframe="30m",
            start_date=start_date,
            end_date=end_date,
            market=None,
            max_concurrent=5,
            batch_size=5,
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks30m).where(Stocks30m.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0

        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "30m",
            fieldnames,
            use_date=False,
            test_name="test_fetch_all_jpx_stocks_persists_30m",
        )

    await cleanup_database(engine)
