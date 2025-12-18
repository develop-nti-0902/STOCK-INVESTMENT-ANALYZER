"""
StockPriceValidator単体テスト

株価データ検証クラスの機能をテストします。
"""

from datetime import datetime, timezone

from app.services.market_data.stock_price.validator import StockPriceValidator


class TestStockPriceValidator:
    """StockPriceValidatorのテストクラス"""

    def setup_method(self):
        """テスト前準備"""
        self.validator = StockPriceValidator()

    def test_validate_valid_data(self):
        """有効なデータの検証"""
        valid_data = {
            "symbol": "7203.T",
            "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open_price": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000000,
            "adj_close": 102.0,
        }

        result = self.validator.validate(valid_data)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_missing_required_fields(self):
        """必須フィールド欠損の検証"""
        invalid_data = {
            "symbol": "7203.T",
            # trade_date が欠損
            "open_price": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000000,
        }

        result = self.validator.validate(invalid_data)

        assert result.is_valid is False
        assert "Required fields are missing" in str(result.errors)

    def test_validate_invalid_symbol(self):
        """無効な銘柄コードの検証"""
        invalid_data = {
            "symbol": "",  # 空文字列
            "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open_price": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000000,
        }

        result = self.validator.validate(invalid_data)

        assert result.is_valid is False
        assert any(
            "symbol" in error and "empty" in error for error in result.errors
        )

    def test_validate_invalid_trade_date(self):
        """無効な取引日時の検証（未来日）"""
        future_date = datetime(2030, 1, 1, tzinfo=timezone.utc)
        invalid_data = {
            "symbol": "7203.T",
            "trade_date": future_date,  # 未来日
            "open_price": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000000,
        }

        result = self.validator.validate(invalid_data)

        assert result.is_valid is False
        assert any(
            "trade_date" in error and "future" in error
            for error in result.errors
        )

    def test_validate_negative_price(self):
        """負の価格データの検証"""
        invalid_data = {
            "symbol": "7203.T",
            "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open_price": -100.0,  # 負の価格
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000000,
        }

        result = self.validator.validate(invalid_data)

        assert result.is_valid is False
        assert any(
            "greater than or equal to 0" in error for error in result.errors
        )

    def test_validate_negative_volume(self):
        """負の出来高の検証"""
        invalid_data = {
            "symbol": "7203.T",
            "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open_price": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": -1000,  # 負の出来高
        }

        result = self.validator.validate(invalid_data)

        assert result.is_valid is False
        assert any(
            "volume" in error and "greater than or equal to 0" in error
            for error in result.errors
        )

    def test_validate_ohlc_integrity_violation(self):
        """OHLC整合性違反の検証"""
        invalid_data = {
            "symbol": "7203.T",
            "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open_price": 110.0,  # 高値より高い
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 1000000,
        }

        result = self.validator.validate(invalid_data)

        assert result.is_valid is False
        assert any(
            "Open price must be within the range" in error
            for error in result.errors
        )

    def test_validate_none_values_allowed(self):
        """None値が許容されることの検証"""
        data_with_none = {
            "symbol": "7203.T",
            "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open_price": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
        }

        result = self.validator.validate(data_with_none)

        # None値は許容されるので、OHLCチェックはスキップされる
        assert result.is_valid is True

    def test_validate_pydantic_model(self):
        """Pydanticモデルの検証"""
        from app.schemas.stock_data import StockPriceCreate

        pydantic_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
        )

        result = self.validator.validate(pydantic_data)

        assert result.is_valid is True

    def test_validate_unsupported_data_type(self):
        """サポートされていないデータ型の検証"""
        result = self.validator.validate("invalid_data")

        assert result.is_valid is False
        assert any(
            "Unsupported data format" in error for error in result.errors
        )
