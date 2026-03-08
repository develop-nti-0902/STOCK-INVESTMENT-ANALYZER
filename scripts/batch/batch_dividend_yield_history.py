"""バッチスクリプト: 配当利回り履歴サービスを実行します。"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.data_synchronization.market_data.dividend_yield_history import (
    DividendYieldHistoryService,
)
from app.utils.database import create_engine

logger = logging.getLogger(__name__)


async def _run(target_date: date) -> None:
    """サービスを実行して結果を永続化します。"""
    engine = create_engine()
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    service = DividendYieldHistoryService(session_maker=session_maker)

    try:
        logger.info("Starting dividend yield history batch for %s", target_date)
        result = await service.generate_for_date(target_date)
        logger.info(
            "Completed dividend yield history batch for %s: "
            "rowcount=%d, skipped=%d, errors=%d, message=%s",
            target_date,
            result.rowcount,
            result.skipped_count,
            result.error_count,
            result.message,
        )
    except Exception:
        logger.exception("Dividend yield history batch failed for %s", target_date)
        raise
    finally:
        await engine.dispose()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run dividend yield history generation for a given date"
    )
    parser.add_argument(
        "--target-date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD format (default: today)",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    args = _parse_args()
    try:
        if args.target_date:
            target_date = datetime.strptime(args.target_date, "%Y-%m-%d").date()
        else:
            target_date = date.today()
    except ValueError as exc:
        logger.error("Invalid target date format: %s", exc)
        raise

    try:
        asyncio.run(_run(target_date))
    except Exception:
        logger.exception("Batch execution terminated with an error")
        raise


if __name__ == "__main__":
    main()
