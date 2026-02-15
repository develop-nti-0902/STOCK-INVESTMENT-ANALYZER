"""初期化スクリプト: 銘柄マスタ全更新 & 全銘柄の 1d 株価を取得してDB保存します.

使い方:
    python -m scripts.init.update_stock_master_and_prices --timeframe 1d --batch-size 500
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.repositories.batch_execution_repository import BatchExecutionRepository
from app.repositories.market_data.stock_master import (
    StockMasterRepository,
    StockMasterUpdatesRepository,
)
from app.services.batch.batch_execution_service import BatchExecutionService
from app.services.market_data.stock_master.service import StockMasterService
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.service import StockPriceService
from app.services.market_data.stock_price.validator import StockPriceValidator
from app.utils.database import close_db, get_engine

logger = logging.getLogger(__name__)


async def _run(timeframe: str = "1d", batch_size: int = 500) -> None:
    """メイン処理: 銘柄マスタを取得 -> 全銘柄の株価(指定timeframe)を取得しDBへ保存します."""
    engine: AsyncEngine = get_engine()
    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )

    async with session_maker() as session:  # type: AsyncSession
        # 1) stock master の取得・保存
        sm_repo = StockMasterRepository(session=session)
        sm_updates_repo = StockMasterUpdatesRepository(session=session)
        stock_master_service = StockMasterService(repo=sm_repo, updates_repo=sm_updates_repo)

        logger.info("Fetching and saving stock master (all JPX)")
        updated_count = await stock_master_service.fetch_and_save()
        # 明示的にコミットして変更を確定する
        try:
            await session.commit()
            logger.info("Stock master updated and committed, records=%s", updated_count)
        except Exception:
            logger.exception("Failed to commit stock master updates; rolling back")
            try:
                await session.rollback()
            except Exception:
                logger.exception("Rollback after failed commit also failed")
            raise

        # Stock price 処理を有効化（全銘柄を処理）
        batch_repo = BatchExecutionRepository(session=session)
        batch_service = BatchExecutionService(repository=batch_repo)

        fetcher = StockPriceFetcher()
        converter = StockPriceConverter()
        validator = StockPriceValidator()
        saver = StockPriceSaver(session=session)

        sp_service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            batch_service=batch_service,
            stock_master_service=stock_master_service,
        )

        logger.info(
            "Starting batch fetch for all JPX symbols: timeframe=%s, batch_size=%s",
            timeframe,
            batch_size,
        )

        # fetch_and_save_for_all_jpxを使って全銘柄を処理
        summary = await sp_service.fetch_and_save_for_all_jpx(
            timeframe=timeframe,
            batch_size=batch_size,
        )

        logger.info(
            "Stock price batch completed: total=%s success=%s failed=%s elapsed=%s",
            summary.get("total"),
            summary.get("success"),
            summary.get("failed"),
            summary.get("elapsed_time"),
        )

        # エラーがある場合はログに出力
        errors = summary.get("errors", [])
        if errors:
            logger.warning("Failed symbols: %d", len(errors))
            for error in errors[:10]:  # 最初の10件だけ表示
                logger.warning("  %s: %s", error.get("symbol"), error.get("errors"))

    # 終了時はデータをそのまま残し、接続プールを破棄してプロセスが正常終了するようにする
    logger.info("Finished run; data retained in DB - disposing engine to exit")
    try:
        await close_db()
    except Exception:
        logger.exception("Failed to dispose DB engine cleanly")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Update stock master and fetch 1d stock prices for all symbols"
    )
    p.add_argument("--timeframe", default="1d", help="Timeframe to fetch (default: 1d)")
    p.add_argument(
        "--batch-size", type=int, default=100, help="Batch size for price fetch (default: 100)"
    )
    return p.parse_args()


def main() -> None:
    """エントリポイント.

    コマンドライン引数を解析して非同期メイン処理を実行する。
    例外はログ出力した上で再送出する。
    """
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    try:
        asyncio.run(_run(timeframe=args.timeframe, batch_size=args.batch_size))
    except Exception as e:
        logger.exception("Script failed: %s", e)
        raise


if __name__ == "__main__":
    main()
