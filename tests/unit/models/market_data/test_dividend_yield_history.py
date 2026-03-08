"""DividendYieldHistory モデル単体テスト。"""

from datetime import date
from decimal import Decimal

from app.models.market_data.dividend_yield_history import DividendYieldHistory


class TestDividendYieldHistoryModel:
    """DividendYieldHistory モデルのテスト."""

    def test_dividend_yield_history_creation(self):
        """DividendYieldHistory オブジェクトの作成テスト."""
        # Arrange
        symbol = "7203.T"
        target_date = date(2024, 1, 1)
        dividend = Decimal("50.00")
        stock_price = Decimal("1500.00")
        dividend_yield = Decimal("0.0333")
        fiscal_year = 2023

        # Act
        history = DividendYieldHistory(
            symbol=symbol,
            date=target_date,
            dividend=dividend,
            stock_price=stock_price,
            dividend_yield=dividend_yield,
            fiscal_year=fiscal_year,
            edinet_document_id=1,
        )

        # Assert
        assert history.symbol == symbol
        assert history.date == target_date
        assert history.dividend == dividend
        assert history.stock_price == stock_price
        assert history.dividend_yield == dividend_yield
        assert history.fiscal_year == fiscal_year
        assert history.edinet_document_id == 1

    def test_dividend_yield_history_with_none_values(self):
        """DividendYieldHistory が NULL 値を許可するテスト."""
        # Arrange
        symbol = "9984.T"
        target_date = date(2024, 1, 1)

        # Act
        history = DividendYieldHistory(
            symbol=symbol,
            date=target_date,
            dividend=None,
            stock_price=None,
            dividend_yield=None,
            fiscal_year=2023,
            edinet_document_id=1,
        )

        # Assert
        assert history.symbol == symbol
        assert history.date == target_date
        assert history.dividend is None
        assert history.stock_price is None
        assert history.dividend_yield is None
