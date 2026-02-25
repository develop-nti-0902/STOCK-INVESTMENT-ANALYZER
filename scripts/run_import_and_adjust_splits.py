import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.market_data.edinet import EdinetStockDividend
from app.services.data_synchronization.market_data.edinet.stock_dividend.saver import (
    EdinetStockDividendSaver,
)
from app.services.data_synchronization.market_data.edinet.stock_dividend.service import (
    EdinetStockDividendService,
)
from app.services.market_data.edinet.stock_split.service import import_stock_splits_from_csv
from app.utils.database import get_database_url


class Stub:
    pass


async def main() -> None:
    engine = create_async_engine(get_database_url(), poolclass=NullPool, echo=False)
    Session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    csv_path = "scripts/stock_splits.csv"

    try:
        async with Session() as session:
            # import stock splits
            imported = await import_stock_splits_from_csv(csv_path, session)
            print(f"Imported rows: {imported}")

            # adjust dividends using same session
            saver = EdinetStockDividendSaver(session)
            service = EdinetStockDividendService(
                parser=Stub(),
                converter=Stub(),
                saver=saver,
                file_manager=Stub(),
                download_service=Stub(),
            )

            adjusted = await service.adjust_dividends_by_splits()
            print(f"Adjusted records: {adjusted}")

            # show sample adjusted rows
            res = await session.execute(
                select(EdinetStockDividend).where(EdinetStockDividend.dividend_adj != None)
            )
            rows = res.scalars().all()
            print(f"Found {len(rows)} adjusted rows (sample up to 10):")
            for r in rows[:10]:
                print(
                    r.sec_code,
                    r.period_end_date,
                    getattr(r, "dividend_actual", None),
                    getattr(r, "dividend_adj", None),
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
