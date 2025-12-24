import csv
import os
from datetime import datetime, timedelta, timezone
from typing import Any, List, Type

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import app.utils.database as db_mod
from app.models.base import Base
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
from app.models.stock_master import StockMaster
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.service import StockPriceService
from app.services.market_data.stock_price.validator import StockPriceValidator
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)

# テスト用の共通銘柄リスト
TEST_SYMBOLS = [
    "7203",  # トヨタ自動車株式会社
    "6758",  # ソニーグループ株式会社
    "9432",  # 日本電信電話株式会社
    "9984",  # ソフトバンクグループ株式会社
    "8306",  # 三菱UFJフィナンシャル・グループ株式会社
    "6861",  # キーエンス株式会社
    "6098",  # リクルートホールディングス株式会社
    "7974",  # 任天堂株式会社
    "6954",  # ファナック株式会社
    "4063",  # 信越化学工業株式会社
]

# TEST_SYMBOLS = [
#     "7203",  # トヨタ自動車株式会社
#     "6758",  # ソニーグループ株式会社
# ]


async def setup_test_database(
    monkeypatch, stock_model_class: Type
) -> AsyncEngine:
    """テスト用データベースのセットアップ"""
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"Skipping integration test: missing DB config ({exc})")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    try:
        db_mod.get_session_maker.cache_clear()
    except Exception:
        pass
    try:
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(delete(stock_model_class))
        await conn.execute(delete(StockMaster))

    return engine


async def register_test_symbols(symbols: List[str]) -> None:
    """テスト用銘柄をstock_masterに登録"""
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        for symbol in symbols:
            master = StockMaster(
                stock_code=symbol,
                stock_name=f"Test Company {symbol}",
                market_category="TSE Prime",
                sector_name_33="Test Industry",
                is_active=1,
            )
            session.add(master)
        await session.commit()
        logger.info(f"Registered {len(symbols)} symbols in stock_master")


async def cleanup_database(engine: AsyncEngine) -> None:
    """データベースのクリーンアップ"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass


def write_csv_artifact(
    rows, timeframe: str, fieldnames: List[str], use_date: bool = False
) -> None:
    """CSVファイルへの結果出力"""
    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(
        artifacts_dir, f"stocks_{timeframe}_multiple_{ts}.csv"
    )

    try:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                row_data = {
                    "id": getattr(r, "id", None),
                    "symbol": getattr(r, "symbol", None),
                    "open": getattr(r, "open", None),
                    "high": getattr(r, "high", None),
                    "low": getattr(r, "low", None),
                    "close": getattr(r, "close", None),
                    "volume": getattr(r, "volume", None),
                    "adj_close": getattr(r, "adj_close", None),
                    "created_at": getattr(r, "created_at", None),
                    "updated_at": getattr(r, "updated_at", None),
                }
                if use_date:
                    row_data["date"] = getattr(r, "date", None)
                else:
                    row_data["timestamp"] = getattr(r, "timestamp", None)
                writer.writerow(row_data)
        logger.info(f"Wrote full dump to {out_path}")
    except Exception as e:
        logger.error(f"Failed to write artifact: {e}")


async def run_stock_price_test(
    monkeypatch,
    timeframe: str,
    stock_model_class: Type,
    start_date,
    end_date,
    use_date: bool = False,
) -> None:
    """
    株価データ取得・保存の統合テストを実行

    Args:
        monkeypatch: pytestのmonkeypatchフィクスチャ
        timeframe: 時間枠（例: "1d", "1h", "15m"）
        stock_model_class: 対象のSQLAlchemyモデルクラス
        start_date: データ取得開始日
        end_date: データ取得終了日
        use_date: Trueの場合は日付フィールド、Falseの場合はタイムスタンプフィールドを使用
    """
    engine = await setup_test_database(monkeypatch, stock_model_class)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
        )

        results = await service.fetch_and_save_multiple(
            symbols=TEST_SYMBOLS,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        total_records_processed = 0
        total_records_saved = 0
        for result in results:
            assert (
                result.success
            ), f"Failed to process {result.symbol}: {result.errors}"
            total_records_processed += result.records_processed
            total_records_saved += result.records_saved
            logger.info(
                f"Processed {result.symbol}: "
                f"{result.records_saved}/{result.records_processed} "
                "records saved"
            )

        expected_count = total_records_processed
        logger.info(
            f"Total processed {expected_count} records for "
            f"{len(TEST_SYMBOLS)} symbols"
        )

        assert total_records_saved >= 0, (
            f"Expected to save 0 or more records, but saved "
            f"{total_records_saved}/{expected_count}"
        )

    async with session_maker() as verify_session:
        all_rows: List[Any] = []
        for result in results:
            symbol = result.symbol
            result_query = await verify_session.execute(
                select(stock_model_class).where(
                    stock_model_class.symbol == symbol
                )
            )
            symbol_rows = result_query.scalars().all()
            all_rows.extend(symbol_rows)

            expected_symbol_count = result.records_processed
            symbol_rate = (
                len(symbol_rows) / expected_symbol_count
                if expected_symbol_count > 0
                else 0
            )
            symbol_msg = (
                f"Expected most records (>95%) for {symbol}, "
                f"but got {len(symbol_rows)}/{expected_symbol_count} "
                f"({symbol_rate:.2%})"
            )
            assert symbol_rate >= 0.95, symbol_msg

            if symbol_rows:
                first_row = symbol_rows[0]
                assert first_row.symbol == symbol
                assert first_row.open is not None
                assert first_row.high is not None
                assert first_row.low is not None
                assert first_row.close is not None

            logger.info(
                f"Verified {len(symbol_rows)} records for {symbol} "
                "persisted correctly"
            )

        persistence_rate = (
            len(all_rows) / expected_count if expected_count > 0 else 0
        )
        assert persistence_rate >= 0.99, (
            f"Expected most rows (>99%) in {stock_model_class.__name__} "
            f"table, but got {len(all_rows)}/{expected_count} "
            f"({persistence_rate:.2%})"
        )

        logger.info(
            f"Verified total {len(all_rows)} records for "
            f"{len(TEST_SYMBOLS)} symbols persisted correctly in "
            f"{stock_model_class.__name__} table"
        )

        if use_date:
            fieldnames = [
                "id",
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adj_close",
                "created_at",
                "updated_at",
            ]
        else:
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

        write_csv_artifact(all_rows, timeframe, fieldnames, use_date)

    await cleanup_database(engine)


async def run_stock_price_single_test(
    monkeypatch,
    timeframe: str,
    stock_model_class: Type,
    start_date,
    end_date,
    use_date: bool = False,
    symbol: str = TEST_SYMBOLS[0],
) -> None:
    """
    株価データ取得・保存の単一銘柄統合テストを実行

    Args:
        monkeypatch: pytestのmonkeypatchフィクスチャ
        timeframe: 時間枠（例: "1d", "1h", "15m"）
        stock_model_class: 対象のSQLAlchemyモデルクラス
        start_date: データ取得開始日
        end_date: データ取得終了日
        use_date: Trueの場合は日付フィールド、Falseの場合はタイムスタンプフィールドを使用
        symbol: テスト対象の銘柄コード
    """
    engine = await setup_test_database(monkeypatch, stock_model_class)
    await register_test_symbols([symbol])

    fetcher = StockPriceFetcher()
    converter = StockPriceConverter()
    validator = StockPriceValidator()

    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        saver = StockPriceSaver(session=session)
        service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            max_concurrent=5,
        )

        result = await service.fetch_and_save_single(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        assert (
            result.success
        ), f"Failed to process {result.symbol}: {result.errors}"
        total_records_processed = result.records_processed
        total_records_saved = result.records_saved
        logger.info(
            f"Processed {result.symbol}: "
            f"{result.records_saved}/{result.records_processed} "
            "records saved"
        )

        expected_count = total_records_processed
        logger.info(
            f"Total processed {expected_count} records for " f"{symbol}"
        )

        assert total_records_saved >= 0, (
            f"Expected to save 0 or more records, but saved "
            f"{total_records_saved}/{expected_count}"
        )

    async with session_maker() as verify_session:
        result_query = await verify_session.execute(
            select(stock_model_class).where(stock_model_class.symbol == symbol)
        )
        symbol_rows = result_query.scalars().all()

        expected_symbol_count = result.records_processed
        symbol_rate = (
            len(symbol_rows) / expected_symbol_count
            if expected_symbol_count > 0
            else 0
        )
        symbol_msg = (
            f"Expected most records (>95%) for {symbol}, "
            f"but got {len(symbol_rows)}/{expected_symbol_count} "
            f"({symbol_rate:.2%})"
        )
        assert symbol_rate >= 0.95, symbol_msg

        if symbol_rows:
            first_row = symbol_rows[0]
            assert first_row.symbol == symbol
            assert first_row.open is not None
            assert first_row.high is not None
            assert first_row.low is not None
            assert first_row.close is not None

        logger.info(
            f"Verified {len(symbol_rows)} records for {symbol} "
            "persisted correctly"
        )

        persistence_rate = (
            len(symbol_rows) / expected_count if expected_count > 0 else 0
        )
        assert persistence_rate >= 0.99, (
            f"Expected most rows (>99%) in {stock_model_class.__name__} "
            f"table, but got {len(symbol_rows)}/{expected_count} "
            f"({persistence_rate:.2%})"
        )

        logger.info(
            f"Verified total {len(symbol_rows)} records for "
            f"{symbol} persisted correctly in "
            f"{stock_model_class.__name__} table"
        )

        if use_date:
            fieldnames = [
                "id",
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adj_close",
                "created_at",
                "updated_at",
            ]
        else:
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

        write_csv_artifact(symbol_rows, timeframe, fieldnames, use_date)

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_and_save_single_1m_stock_data(monkeypatch):
    """
    統合テスト: 1m株価データを単一銘柄でフェッチしてStocks1mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=3)
    await run_stock_price_single_test(
        monkeypatch, "1m", Stocks1m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_5m_stock_data(monkeypatch):
    """
    統合テスト: 5m株価データを単一銘柄でフェッチしてStocks5mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=7)
    await run_stock_price_single_test(
        monkeypatch, "5m", Stocks5m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_15m_stock_data(monkeypatch):
    """
    統合テスト: 15m株価データを単一銘柄でフェッチしてStocks15mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=14)
    await run_stock_price_single_test(
        monkeypatch, "15m", Stocks15m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_30m_stock_data(monkeypatch):
    """
    統合テスト: 30m株価データを単一銘柄でフェッチしてStocks30mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    await run_stock_price_single_test(
        monkeypatch, "30m", Stocks30m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_1h_stock_data(monkeypatch):
    """
    統合テスト: 1h株価データを単一銘柄でフェッチしてStocks1hテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=90)
    await run_stock_price_single_test(
        monkeypatch, "1h", Stocks1h, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_1d_stock_data(monkeypatch):
    """
    統合テスト: 1d株価データを単一銘柄でフェッチしてStocks1dテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    await run_stock_price_single_test(
        monkeypatch, "1d", Stocks1d, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_1wk_stock_data(monkeypatch):
    """
    統合テスト: 1wk株価データを単一銘柄でフェッチしてStocks1wkテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365)
    await run_stock_price_single_test(
        monkeypatch, "1wk", Stocks1wk, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_single_1mo_stock_data(monkeypatch):
    """
    統合テスト: 1mo株価データを単一銘柄でフェッチしてStocks1moテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365 * 2)
    await run_stock_price_single_test(
        monkeypatch, "1mo", Stocks1mo, start_date, end_date, use_date=False
    )
    """
    統合テスト: 1m株価データをフェッチしてStocks1mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=3)
    await run_stock_price_test(
        monkeypatch, "1m", Stocks1m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_5m_stock_data(monkeypatch):
    """
    統合テスト: 5m株価データをフェッチしてStocks5mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=7)
    await run_stock_price_test(
        monkeypatch, "5m", Stocks5m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_15m_stock_data(monkeypatch):
    """
    統合テスト: 15m株価データをフェッチしてStocks15mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=14)
    await run_stock_price_test(
        monkeypatch, "15m", Stocks15m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_30m_stock_data(monkeypatch):
    """
    統合テスト: 30m株価データをフェッチしてStocks30mテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    await run_stock_price_test(
        monkeypatch, "30m", Stocks30m, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_1h_stock_data(monkeypatch):
    """
    統合テスト: 1h株価データをフェッチしてStocks1hテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=90)
    await run_stock_price_test(
        monkeypatch, "1h", Stocks1h, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_1d_stock_data(monkeypatch):
    """
    統合テスト: 1d株価データをフェッチしてStocks1dテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    await run_stock_price_test(
        monkeypatch, "1d", Stocks1d, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_1wk_stock_data(monkeypatch):
    """
    統合テスト: 1wk株価データをフェッチしてStocks1wkテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365)
    await run_stock_price_test(
        monkeypatch, "1wk", Stocks1wk, start_date, end_date, use_date=False
    )


@pytest.mark.anyio
async def test_fetch_and_save_1mo_stock_data(monkeypatch):
    """
    統合テスト: 1mo株価データをフェッチしてStocks1moテーブルへ保存
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365 * 2)
    await run_stock_price_test(
        monkeypatch, "1mo", Stocks1mo, start_date, end_date, use_date=False
    )
