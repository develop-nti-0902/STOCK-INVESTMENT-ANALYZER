"""Tests for StockSplitRepository."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.core.base import Base
from app.models.market_data.edinet.stock_split import StockSplit
from app.repositories.market_data.edinet.stock_split_repository import StockSplitRepository


@pytest.mark.asyncio
async def test_stock_split_repository_upsert_and_find(tmp_path) -> None:
    """Test upsert and find operations on StockSplitRepository."""
    url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with AsyncSessionMaker() as session:
        repo = StockSplitRepository(session)

        payload = {
            "code": "37980",
            "effective_date": date(2023, 10, 1),
            "ratio_from": 1,
            "ratio_to": 2,
        }

        created = await repo.upsert(payload)
        assert isinstance(created, StockSplit)

        found = await repo.find_by_code("37980")
        assert len(found) == 1

        by_date = await repo.find_by_date("37980", date(2023, 10, 1))
        assert by_date is not None
        assert by_date.ratio_to == 2
