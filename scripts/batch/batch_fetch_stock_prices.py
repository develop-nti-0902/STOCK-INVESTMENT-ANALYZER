"""バッチスクリプト: 全銘柄の株価データを指定期間で取得してDB保存します.

デフォルトでは過去7日分のデータを取得します。

使い方:
    # 過去7日分のデータを取得（デフォルト）
    python -m scripts.batch.batch_fetch_stock_prices

    # 過去30日分のデータを取得
    python -m scripts.batch.batch_fetch_stock_prices --days 30

    # バッチサイズとタイムフレームを指定
    python -m scripts.batch.batch_fetch_stock_prices --days 7 --timeframe 1d
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.repositories.market_data.stock_master import (
    StockMasterRepository,
    StockMasterUpdatesRepository,
)
from app.services.market_data.stock_master.service import StockMasterService
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.service import StockPriceService
from app.services.market_data.stock_price.validator import StockPriceValidator
from app.utils.database import close_db, get_engine

logger = logging.getLogger(__name__)


async def _run(
    days: int = 7,
    timeframe: str = "1d",
    batch_size: int = 1000,
) -> None:
    """メイン処理: 指定した期間で全銘柄の株価データを取得しDBへ保存します.

    Args:
        days: 取得する日数（デフォルト: 7日）
        timeframe: タイムフレーム（デフォルト: 1d）
        batch_size: バッチサイズ（デフォルト: 1000）
    """
    engine: AsyncEngine = get_engine()
    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )

    # periodパラメータの構築（例: "7d", "30d"）
    period = f"{days}d"

    logger.info(
        "Starting batch fetch for all JPX symbols: period=%s, timeframe=%s, batch_size=%s",
        period,
        timeframe,
        batch_size,
    )

    async with session_maker() as session:  # type: AsyncSession
        # リポジトリとサービスの初期化
        sm_repo = StockMasterRepository(session=session)
        sm_updates_repo = StockMasterUpdatesRepository(session=session)
        stock_master_service = StockMasterService(repo=sm_repo, updates_repo=sm_updates_repo)

        fetcher = StockPriceFetcher()
        converter = StockPriceConverter()
        validator = StockPriceValidator()
        saver = StockPriceSaver(session=session)

        sp_service = StockPriceService(
            fetcher=fetcher,
            saver=saver,
            converter=converter,
            validator=validator,
            stock_master_service=stock_master_service,
        )

        # fetch_and_save_for_all_jpxを使って全銘柄を処理
        summary = await sp_service.fetch_and_save_for_all_jpx(
            timeframe=timeframe,
            batch_size=batch_size,
            period=period,
        )

        logger.info(
            "Batch processing completed: total=%s, success=%s, failed=%s, elapsed=%s",
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

    # エンジンをクリーンアップ
    logger.info("Disposing database engine")
    try:
        await close_db()
    except Exception:
        logger.exception("Failed to dispose DB engine cleanly")


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースします."""
    p = argparse.ArgumentParser(
        description="Fetch stock prices for all JPX symbols for a specified period"
    )
    p.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to fetch (default: 7)",
    )
    p.add_argument(
        "--timeframe",
        type=str,
        default="1d",
        help="Timeframe to fetch (default: 1d)",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for processing (default: 100)",
    )
    return p.parse_args()


def main() -> None:
    """エントリポイント.

    コマンドライン引数を解析して非同期メイン処理を実行する。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    args = _parse_args()

    try:
        asyncio.run(
            _run(
                days=args.days,
                timeframe=args.timeframe,
                batch_size=args.batch_size,
            )
        )
    except Exception as e:
        logger.exception("Script failed: %s", e)
        raise


if __name__ == "__main__":
    main()
