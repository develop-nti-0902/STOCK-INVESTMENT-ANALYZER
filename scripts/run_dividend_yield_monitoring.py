"""配当利回り監視サービスを CLI で実行するスクリプト."""

import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.monitoring.dividend_yield_monitoring_service import DividendYieldMonitoringService
from app.utils.database import create_engine


async def main() -> None:
    engine = create_engine()
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    service = DividendYieldMonitoringService(session_maker=session_maker)
    try:
        await service.run(date.today())
    except KeyboardInterrupt:
        print("[DEBUG] dividend yield monitoring interrupted by user")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
