"""Tests for StockSplit service."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.core.base import Base
from app.services.market_data.edinet.stock_split.service import import_stock_splits_from_csv


@pytest.mark.asyncio
async def test_import_stock_splits_from_csv(tmp_path: Path) -> None:
    """Test CSV import function."""
    csv_path = tmp_path / "splits.csv"
    csv_content = "code,effective_date,ratio_from,ratio_to\n37980,2023-10-01,1,2\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with AsyncSessionMaker() as session:
        count = await import_stock_splits_from_csv(str(csv_path), session)
        assert count == 1

        # verify row exists
        res = await session.execute(
            text("SELECT code, ratio_to FROM stock_split WHERE code='37980'")
        )
        row = res.fetchone()
        assert row is not None
        assert row[1] == 2
