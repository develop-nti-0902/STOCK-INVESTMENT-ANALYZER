"""StockData モデルの単体テスト."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base,
    StockMaster,
    Stocks1d,
    Stocks1h,
    Stocks1m,
    Stocks1mo,
    Stocks1wk,
    Stocks5m,
    Stocks15m,
    Stocks30m,
)


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    return Session()


@pytest.mark.parametrize(
    "model",
    [Stocks1m, Stocks5m, Stocks15m, Stocks30m, Stocks1h],
)
def test_time_based_models_crud(model):
    """時間単位の株価モデルでCRUDが動作することを確認する."""
    session = _make_session()
    with session:
        session.add(
            StockMaster(
                stock_code="TM1",
                stock_name="TimeTest",
                is_active=1,
            )
        )
        session.flush()

        from datetime import timezone

        ts = datetime.now(timezone.utc)
        entry = model(
            symbol="TM1",
            timestamp=ts,
            open=Decimal("10.00"),
            high=Decimal("11.00"),
            low=Decimal("9.50"),
            close=Decimal("10.50"),
            volume=123,
        )

        session.add(entry)
        session.commit()

        q = session.query(model).filter_by(symbol="TM1").one()
        assert q.close == Decimal("10.50")


@pytest.mark.parametrize("model", [Stocks1d, Stocks1wk, Stocks1mo])
def test_date_based_models_crud(model):
    """日付ベースの株価モデルでCRUDが動作することを確認する."""
    session = _make_session()
    with session:
        session.add(
            StockMaster(
                stock_code="DM1",
                stock_name="DateTest",
                is_active=1,
            )
        )
        session.flush()

        from datetime import timezone

        d = date.today()
        ts = datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)
        entry = model(
            symbol="DM1",
            timestamp=ts,
            open=Decimal("200.00"),
            high=Decimal("210.00"),
            low=Decimal("190.00"),
            close=Decimal("205.00"),
            volume=2000,
        )

        session.add(entry)
        session.commit()

        q = session.query(model).filter_by(symbol="DM1").one()
        assert q.close == Decimal("205.00")


@pytest.mark.parametrize(
    "model, is_date",
    [
        (Stocks1m, False),
        (Stocks5m, False),
        (Stocks15m, False),
        (Stocks30m, False),
        (Stocks1h, False),
        (Stocks1d, True),
        (Stocks1wk, True),
        (Stocks1mo, True),
    ],
)
def test_unique_constraint_per_model(model, is_date):
    """各モデルに一意制約が機能することを確認する."""
    session = _make_session()
    with session:
        session.add(
            StockMaster(
                stock_code="UQ1",
                stock_name="UniqueTest",
                is_active=1,
            )
        )
        session.flush()

        from datetime import timezone

        key = datetime.now(timezone.utc)
        a = model(
            symbol="UQ1",
            timestamp=key,
            open=Decimal("1.00"),
            high=Decimal("2.00"),
            low=Decimal("1.00"),
            close=Decimal("1.50"),
            volume=1,
        )
        session.add(a)
        session.commit()

        b = model(
            symbol="UQ1",
            timestamp=key,
            open=Decimal("1.00"),
            high=Decimal("2.00"),
            low=Decimal("1.00"),
            close=Decimal("1.50"),
            volume=1,
        )
        session.add(b)

        with pytest.raises(IntegrityError):
            session.commit()
