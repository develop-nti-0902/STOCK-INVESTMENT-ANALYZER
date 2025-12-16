import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.models.base import Base
from app.models.stock_data import Stocks1mo
from app.repositories.stock_data_repository import StockData1moRepository
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)


@pytest.mark.anyio
async def test_fetch_and_save_1mo_stock_data(monkeypatch):
    """
    統合テスト: yfinanceから1mo株価データをフェッチし、Stocks1moテーブルへ保存するまでの
    一連の流れを検証する。
    """

    try:
        DATABASE_URL = db_mod.get_database_url()
    except (
        Exception
    ) as exc:  # pragma: no cover - 環境変数未設定時は明示的に失敗させる
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
        from sqlalchemy import delete

        from app.models.stock_master import StockMaster

        await conn.execute(delete(Stocks1mo))
        await conn.execute(delete(StockMaster))

    test_symbols = [
        "7203.T",
        "9984.T",
        "6758.T",
        "9433.T",
        "8306.T",
        "6861.T",
        "6954.T",
        "4063.T",
        "6902.T",
        "7741.T",
    ]
    timeframe = "1mo"
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365 * 2)

    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        from app.models.stock_master import StockMaster

        for symbol in test_symbols:
            master = StockMaster(
                stock_code=symbol,
                stock_name=f"Test Company {symbol}",
                market_category="TSE Prime",
                sector_name_33="Test Industry",
                is_active=1,
            )
            session.add(master)

        await session.commit()
        logger.info(f"Registered {len(test_symbols)} symbols in stock_master")

    fetcher = StockPriceFetcher()
    all_stock_data = await fetcher.fetch_batch(
        symbols=test_symbols,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    total_records = 0
    for symbol in test_symbols:
        stock_data_list = all_stock_data.get(symbol, [])
        assert len(stock_data_list) > 0, (
            f"No data fetched for {symbol} between {start_date} and "
            f"{end_date}"
        )
        total_records += len(stock_data_list)
        logger.info(
            f"Fetched {len(stock_data_list)} records for {symbol} from "
            "Yahoo Finance"
        )

    expected_count = total_records

    async with session_maker() as session:
        repo = StockData1moRepository(session=session)

        all_db_records = []
        for symbol, stock_data_list in all_stock_data.items():
            for data in stock_data_list:
                all_db_records.append(
                    {
                        "symbol": symbol,
                        "date": (
                            data.trade_date.date()
                            if hasattr(data.trade_date, "date")
                            else data.trade_date
                        ),
                        "open": data.open_price,
                        "high": data.high,
                        "low": data.low,
                        "close": data.close,
                        "volume": data.volume,
                        "adj_close": data.adj_close,
                    }
                )

        saved_count = await repo.upsert_bulk(all_db_records)

        success_rate = (
            saved_count / expected_count if expected_count > 0 else 0
        )
        assert success_rate > 0.99, (
            f"Expected to save most records (>99%), but only saved "
            f"{saved_count}/{expected_count} ({success_rate:.2%})"
        )

    async with session_maker() as verify_session:
        all_rows = []
        for symbol in test_symbols:
            result = await verify_session.execute(
                select(Stocks1mo).where(Stocks1mo.symbol == symbol)
            )
            symbol_rows = result.scalars().all()
            all_rows.extend(symbol_rows)

            expected_symbol_count = len(all_stock_data[symbol])
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
            assert symbol_rate > 0.95, symbol_msg

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
        assert persistence_rate > 0.99, (
            f"Expected most rows (>99%) in Stocks1mo table, but got "
            f"{len(all_rows)}/{expected_count} ({persistence_rate:.2%})"
        )

        rows = all_rows

        import csv

        artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(artifacts_dir, f"stocks_1mo_multiple_{ts}.csv")

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

        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow(
                        {
                            "id": getattr(r, "id", None),
                            "symbol": getattr(r, "symbol", None),
                            "date": getattr(r, "date", None),
                            "open": getattr(r, "open", None),
                            "high": getattr(r, "high", None),
                            "low": getattr(r, "low", None),
                            "close": getattr(r, "close", None),
                            "volume": getattr(r, "volume", None),
                            "adj_close": getattr(r, "adj_close", None),
                            "created_at": getattr(r, "created_at", None),
                            "updated_at": getattr(r, "updated_at", None),
                        }
                    )
            logger.info(f"Wrote full dump to {out_path}")
        except Exception as e:  # pragma: no cover - artifact write
            logger.error(f"Failed to write artifact: {e}")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass
