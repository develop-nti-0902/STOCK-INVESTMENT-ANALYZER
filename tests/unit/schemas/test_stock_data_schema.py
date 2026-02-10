"""
株価データスキーマの単体テスト

StockPriceBase, StockPriceCreate, StockPriceResponse, StockPriceBatch,
およびタイムフレーム別スキーマのテストを行います。
"""

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
    """StockPriceBaseスキーマのテスト"""

    def test_valid_data(self):
        """有効なデータで作成できることを確認"""
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
        """オプションのフィールドがNoneでも作成できることを確認"""
        data = {
            "symbol": "AAPL",
            "timestamp": datetime(2023, 1, 1, 12, 0, 0),
        }
        stock = StockPriceBase(**data)
        assert stock.open_price is None
        assert stock.volume is None


class TestStockPriceCreate:
    """StockPriceCreateスキーマのテスト"""

    def test_valid_data(self):
        """有効なデータで作成できることを確認"""
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
        """無効な銘柄コードでエラーが発生することを確認"""
        data = {
            "symbol": "",  # 空文字
            "trade_date": datetime(2023, 1, 1, 12, 0, 0),
        }
        with pytest.raises(ValidationError):
            StockPriceCreate(**data)


class TestStockPriceResponse:
    """StockPriceResponseスキーマのテスト"""

    def test_with_id_and_timestamps(self):
        """IDとタイムスタンプ付きで作成できることを確認"""
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
    """StockPriceBatchスキーマのテスト"""

    def test_valid_batch(self):
        """有効なバッチデータで作成できることを確認"""
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
        """無効な時間軸でエラーが発生することを確認"""
        data = {
            "symbol": "AAPL",
            "timeframe": "invalid",  # 無効な時間軸
            "data": [],
        }
        with pytest.raises(ValidationError):
            StockPriceBatch(**data)


class TestTimeframeSchemas:
    """タイムフレーム別スキーマのテスト"""

    def test_timeframe_schemas_creation(self):
        """各タイムフレームスキーマが作成できることを確認"""
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
