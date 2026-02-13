"""Unit tests for stock data schemas and timeframe variants."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.stock_data import (
    StockPrice1D,
    StockPrice1H,
    StockPrice1M,
    StockPrice1MO,
    StockPrice1WK,
    StockPrice5M,
    StockPrice15M,
    StockPriceBase,
    StockPriceBatch,
    StockPriceCreate,
    StockPriceResponse,
)


class TestStockPriceBase:
    """Tests for `StockPriceBase` schema."""

    def test_valid_data(self):
        """Create `StockPriceBase` with valid data."""
        data = {
            "symbol": "AAPL",
            "timestamp": datetime(2023, 1, 1, 12, 0, 0),
            "open_price": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 152.0,
            "volume": 1000000,
            "adj_close": 152.0,
        }
        stock = StockPriceBase(**data)
        assert stock.symbol == "AAPL"
        assert stock.open_price == 150.0
        assert stock.close == 152.0

    def test_optional_fields(self):
        """Allow optional fields to be None."""
        data = {
            "symbol": "AAPL",
            "timestamp": datetime(2023, 1, 1, 12, 0, 0),
        }
        stock = StockPriceBase(**data)
        assert stock.open_price is None
        assert stock.volume is None


class TestStockPriceCreate:
    """Tests for `StockPriceCreate` schema."""

    def test_valid_data(self):
        """Normalize and validate symbol casing on create."""
        data = {
            "symbol": "aapl",  # 小文字で入力
            "timestamp": datetime(2023, 1, 1, 12, 0, 0),
            "open_price": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 152.0,
            "volume": 1000000,
            "adj_close": 152.0,
        }
        stock = StockPriceCreate(**data)
        assert stock.symbol == "AAPL"  # 大文字に変換される

    def test_invalid_symbol(self):
        """Raise ValidationError for invalid symbol values."""
        data = {
            "symbol": "",  # 空文字
            "trade_date": datetime(2023, 1, 1, 12, 0, 0),
        }
        with pytest.raises(ValidationError):
            StockPriceCreate(**data)


class TestStockPriceResponse:
    """Tests for `StockPriceResponse` schema."""

    def test_with_id_and_timestamps(self):
        """Create response with id and timestamp fields."""
        data = {
            "id": 1,
            "symbol": "AAPL",
            "timestamp": datetime(2023, 1, 1, 12, 0, 0),
            "created_at": datetime(2023, 1, 1, 10, 0, 0),
            "updated_at": datetime(2023, 1, 1, 11, 0, 0),
            "close": 152.0,
        }
        stock = StockPriceResponse(**data)
        assert stock.id == 1
        assert stock.created_at is not None
        assert stock.updated_at is not None


class TestStockPriceBatch:
    """Tests for `StockPriceBatch` schema."""

    def test_valid_batch(self):
        """Create a valid stock price batch."""
        data = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "data": [
                {
                    "symbol": "AAPL",
                    "timestamp": datetime(2023, 1, 1, 12, 0, 0),
                    "close": 152.0,
                }
            ],
        }
        batch = StockPriceBatch(**data)
        assert batch.symbol == "AAPL"
        assert batch.timeframe == "1d"
        assert len(batch.data) == 1

    def test_invalid_timeframe(self):
        """Raise ValidationError for invalid timeframe values."""
        data = {
            "symbol": "AAPL",
            "timeframe": "invalid",  # 無効な時間軸
            "data": [],
        }
        with pytest.raises(ValidationError):
            StockPriceBatch(**data)


class TestTimeframeSchemas:
    """Tests for timeframe-specific stock price schemas."""

    def test_timeframe_schemas_creation(self):
        """Instantiate each timeframe schema with base data."""
        base_data = {
            "symbol": "AAPL",
            "timestamp": datetime(2023, 1, 1, 12, 0, 0),
            "close": 152.0,
        }

        # 各スキーマをテスト
        schemas = [
            StockPrice1M,
            StockPrice5M,
            StockPrice15M,
            StockPrice1H,
            StockPrice1D,
            StockPrice1WK,
            StockPrice1MO,
        ]

        for schema_class in schemas:
            stock = schema_class(**base_data)
            assert stock.symbol == "AAPL"
            assert stock.close == 152.0
