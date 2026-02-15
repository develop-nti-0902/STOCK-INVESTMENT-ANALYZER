"""Tests for the `StockMasterUpdates` model fields and defaults."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_stock_master_updates_fields_and_defaults():
    """StockMasterUpdates のフィールドとデフォルト値が期待通りか検証する."""
    engine = create_engine("sqlite:///:memory:", future=True)

    from app.models import Base, StockMasterUpdates  # noqa: E402

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    smu = StockMasterUpdates(
        update_type="FULL",
        total_stocks=100,
        status="running",
    )
    session.add(smu)
    session.commit()
    session.refresh(smu)

    assert smu.id is not None
    assert smu.update_type == "FULL"
    assert smu.total_stocks == 100
    assert smu.added_stocks == 0
    assert smu.updated_stocks == 0
    assert smu.removed_stocks == 0
    assert smu.status == "running"
    assert smu.started_at is not None

    session.close()
