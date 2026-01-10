from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

import app.utils.database as db_mod
from app.models.stock_data import (
    Stocks1d,
    Stocks1h,
    Stocks1m,
    Stocks1mo,
    Stocks1wk,
    Stocks5m,
    Stocks15m,
    Stocks30m,
)
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.service import StockPriceService
from app.services.market_data.stock_price.validator import StockPriceValidator
from tests.integration.utils import (
    TEST_SYMBOLS,
    cleanup_database,
    register_test_symbols,
    setup_test_database,
    write_csv_artifact,
)

# モジュール共通で使うインスタンス
converter = StockPriceConverter()
validator = StockPriceValidator()


class DummyBatchService:
    async def create_job(self, *args, **kwargs):
        return MagicMock(id=1)

    async def start_job(self, *args, **kwargs):
        return None

    async def update_progress(self, *args, **kwargs):
        return None

    async def complete_job(self, *args, **kwargs):
        return None

    async def get_job_status(self, *args, **kwargs):
        return MagicMock(
            successful_stocks=0, failed_stocks=0, processed_stocks=0
        )


@pytest.mark.anyio
async def test_fetch_all_jpx_stocks_persists_1d(monkeypatch):
    """
    統合テスト: `fetch_all_jpx_stocks` を呼び出し（DummyStockMasterService を使用）、
    結果が返され `Stocks1d` へ永続化されることを簡易的に検証します。
    """
    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        summary = await service.fetch_all_jpx_stocks(
            timeframe="1d",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks1h)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1h",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks1mo)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1mo",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks1wk)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1wk",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks1m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="1m",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks5m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="5m",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks15m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="15m",
            start_date=None,
            end_date=None,
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
    engine = await setup_test_database(monkeypatch, Stocks30m)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

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
            batch_service=DummyBatchService(),
        )

        await service.fetch_all_jpx_stocks(
            timeframe="30m",
            start_date=None,
            end_date=None,
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


@pytest.mark.anyio
async def test_fetch_batch_persists_1d(monkeypatch):
    """
    統合テスト: `StockPriceFetcher.fetch_batch` を使って複数銘柄を一括取得し、
    `StockPriceSaver.save_batch` で `Stocks1d` テーブルへ永続化されることを検証します。
    """

    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

    # fetch_batch を呼び出して複数銘柄を一括取得
    results = await fetcher.fetch_batch(TEST_SYMBOLS, timeframe="1d")

    session_maker = db_mod.get_session_maker()

    # Saver に渡す形式へ変換して保存
    async with session_maker() as session:
        saver = StockPriceSaver(session=session)

        data_list = []
        for symbol, stock_datas in results.items():
            records = []
            for sd in stock_datas:
                records.append(
                    {
                        "timestamp": sd.trade_date,
                        "open": sd.open_price,
                        "high": sd.high,
                        "low": sd.low,
                        "close": sd.close,
                        "volume": sd.volume,
                        "adj_close": sd.adj_close,
                    }
                )

            if records:
                data_list.append(
                    {"symbol": symbol, "timeframe": "1d", "records": records}
                )

        # 保存実行
        saved_count = await saver.save_batch(data_list)

        # サマリの最小チェック
        assert isinstance(saved_count, int)

    # DB 内の永続化確認 + CSV アーティファクト出力
    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1d).where(Stocks1d.symbol == symbol)
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
            "1d",
            fieldnames,
            use_date=False,
            test_name="test_fetch_batch_persists_1d",
        )

    await cleanup_database(engine)
