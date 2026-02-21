"""バッチスクリプト: 配当利回り監視サービスを定期的に実行します."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.monitoring.dividend_yield_monitoring_service import DividendYieldMonitoringService
from app.utils.database import create_engine

logger = logging.getLogger(__name__)


async def _run(monitoring_date: date) -> None:
    """サービスを実行して結果を永続化します."""
    engine = create_engine()
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    service = DividendYieldMonitoringService(session_maker=session_maker)

    try:
        logger.info("Starting dividend yield monitoring batch for %s", monitoring_date)
        await service.run(monitoring_date)
        logger.info("Completed dividend yield monitoring batch for %s", monitoring_date)
    except Exception:
        logger.exception("Dividend yield monitoring batch failed for %s", monitoring_date)
        raise
    finally:
        await engine.dispose()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run dividend yield monitoring for a given date")
    parser.add_argument(
        "--monitoring-date",
        type=str,
        default=None,
        help="Monitoring date in YYYY-MM-DD format (default: today)",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    args = _parse_args()
    try:
        if args.monitoring_date:
            monitoring_date = datetime.strptime(args.monitoring_date, "%Y-%m-%d").date()
        else:
            monitoring_date = date.today()
    except ValueError as exc:
        logger.error("Invalid monitoring date format: %s", exc)
        raise

    try:
        asyncio.run(_run(monitoring_date))
    except Exception:
        logger.exception("Batch execution terminated with an error")
        raise


if __name__ == "__main__":
    main()
