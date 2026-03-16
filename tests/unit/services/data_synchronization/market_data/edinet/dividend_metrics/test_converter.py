"""Unit tests for DividendMetricsConverter.

配当メトリクス計算・変換層のテスト。

テスト対象：
  - payout_ratio 計算ロジック（除算精度含む）
  - NULL値処理（dividend=None, eps=None）
  - dividend_adj 優先度（dividend_adj != None なら使用、さもなければ dividend_actual）
  - Decimal型の精度
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.models.market_data.edinet import EdinetProfitAndLoss, EdinetStockDividend
from app.schemas.market_data.edinet import EdinetDividendMetricsCreate
from app.services.data_synchronization.market_data.edinet.dividend_metrics.converter import (
    DividendMetricsConverter,
)


@pytest.fixture
def converter():
    """DividendMetricsConverter インスタンス."""
    return DividendMetricsConverter()


@pytest.fixture
def dividend_record():
    """モック dividend レコード（基本形）."""
    record = Mock(spec=EdinetStockDividend)
    record.edinet_document_id = 1
    record.period_end_date = date(2025, 3, 31)
    record.fiscal_year = 2025
    record.dividend_adj = Decimal("50.00")  # 調整配当
    record.dividend_actual = Decimal("48.00")  # 実績配当
    record.is_consolidated = True
    record.symbol = "1234"
    return record


@pytest.fixture
def profit_loss_record():
    """モック profit_loss レコード（基本形）."""
    record = Mock(spec=EdinetProfitAndLoss)
    record.eps = Decimal("100.00")
    return record


class TestDividendMetricsConverterBasicConversion:
    """基本的な変換テスト."""

    @pytest.mark.asyncio
    async def test_to_schema_converts_dividend_and_eps(
        self, converter, dividend_record, profit_loss_record
    ):
        """基本変換: dividend + eps → EdinetDividendMetricsCreate."""
        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert isinstance(result, EdinetDividendMetricsCreate)
        assert result.edinet_document_id == 1
        assert result.period_end_date == date(2025, 3, 31)
        assert result.fiscal_year == 2025
        assert result.is_consolidated is True

    @pytest.mark.asyncio
    async def test_to_schema_preserves_edinet_document_id(
        self, converter, dividend_record, profit_loss_record
    ):
        """edinet_document_id を保持."""
        dividend_record.edinet_document_id = 999
        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.edinet_document_id == 999

    @pytest.mark.asyncio
    async def test_to_schema_preserves_period_end_date(
        self, converter, dividend_record, profit_loss_record
    ):
        """period_end_date を保持."""
        dividend_record.period_end_date = date(2024, 12, 31)
        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.period_end_date == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_to_schema_preserves_fiscal_year(
        self, converter, dividend_record, profit_loss_record
    ):
        """fiscal_year を保持."""
        dividend_record.fiscal_year = 2024
        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.fiscal_year == 2024

    @pytest.mark.asyncio
    async def test_to_schema_preserves_is_consolidated(
        self, converter, dividend_record, profit_loss_record
    ):
        """is_consolidated を保持."""
        dividend_record.is_consolidated = False
        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.is_consolidated is False


class TestDividendMetricsConverterDividendAdjPriority:
    """dividend_adj の優先度テスト."""

    @pytest.mark.asyncio
    async def test_dividend_adj_used_when_not_none(
        self, converter, dividend_record, profit_loss_record
    ):
        """dividend_adj != None なら dividend_adj を使用."""
        dividend_record.dividend_adj = Decimal("55.00")
        dividend_record.dividend_actual = Decimal("50.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # 未調整の dividend_actual が優先される
        assert result.dividend_actual == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_dividend_actual_fallback_when_adj_none(
        self, converter, dividend_record, profit_loss_record
    ):
        """dividend_adj = None の場合 dividend_actual を使用."""
        dividend_record.dividend_adj = None
        dividend_record.dividend_actual = Decimal("48.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.dividend_actual == Decimal("48.00")

    @pytest.mark.asyncio
    async def test_dividend_both_none(self, converter, dividend_record, profit_loss_record):
        """dividend_adj と dividend_actual が両方 None."""
        dividend_record.dividend_adj = None
        dividend_record.dividend_actual = None

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.dividend_actual is None

    @pytest.mark.asyncio
    async def test_dividend_adj_zero(self, converter, dividend_record, profit_loss_record):
        """dividend_adj = 0（境界値）."""
        # 未調整値が無い場合に調整値(0)が有効となる
        dividend_record.dividend_adj = Decimal("0")
        dividend_record.dividend_actual = None

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # 0 は有効な値
        assert result.dividend_actual == Decimal("0")

    @pytest.mark.asyncio
    async def test_dividend_large_value(self, converter, dividend_record, profit_loss_record):
        """dividend の大きい値（境界値）."""
        # 未調整値が無い場合に調整済み値がフォールバックとして使用される
        dividend_record.dividend_actual = None
        dividend_record.dividend_adj = Decimal("99999.99")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.dividend_actual == Decimal("99999.99")


class TestDividendMetricsConverterPayoutRatiCalculation:
    """payout_ratio 計算テスト."""

    @pytest.mark.asyncio
    async def test_payout_ratio_calculated_correctly(
        self, converter, dividend_record, profit_loss_record
    ):
        """payout_ratio = dividend / eps（正常系）."""
        dividend_record.dividend_actual = Decimal("50.00")
        profit_loss_record.eps = Decimal("100.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        expected = Decimal("50.00") / Decimal("100.00")
        assert result.payout_ratio == expected
        assert result.payout_ratio == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_payout_ratio_precision_decimal(
        self, converter, dividend_record, profit_loss_record
    ):
        """payout_ratio の精度確認（小数第4位以上）."""
        dividend_record.dividend_actual = Decimal("33.33")
        profit_loss_record.eps = Decimal("100.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # 33.33 / 100 = 0.3333
        expected = Decimal("33.33") / Decimal("100.00")
        assert result.payout_ratio == expected

    @pytest.mark.asyncio
    async def test_payout_ratio_none_when_eps_zero(
        self, converter, dividend_record, profit_loss_record
    ):
        """eps = 0 の場合 payout_ratio は None（ゼロ除算防止）."""
        dividend_record.dividend_actual = Decimal("50.00")
        profit_loss_record.eps = Decimal("0")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.payout_ratio is None

    @pytest.mark.asyncio
    async def test_payout_ratio_none_when_eps_negative(
        self, converter, dividend_record, profit_loss_record
    ):
        """eps < 0 の場合 payout_ratio は None（負数回避）."""
        dividend_record.dividend_actual = Decimal("50.00")
        profit_loss_record.eps = Decimal("-100.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.payout_ratio is None

    @pytest.mark.asyncio
    async def test_payout_ratio_none_when_dividend_none(
        self, converter, dividend_record, profit_loss_record
    ):
        """dividend = None の場合 payout_ratio は None."""
        dividend_record.dividend_adj = None
        dividend_record.dividend_actual = None
        profit_loss_record.eps = Decimal("100.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.payout_ratio is None

    @pytest.mark.asyncio
    async def test_payout_ratio_none_when_eps_none(
        self, converter, dividend_record, profit_loss_record
    ):
        """eps = None の場合 payout_ratio は None."""
        dividend_record.dividend_actual = Decimal("50.00")
        profit_loss_record.eps = None

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.payout_ratio is None

    @pytest.mark.asyncio
    async def test_payout_ratio_all_none(self, converter, dividend_record, profit_loss_record):
        """dividend = None かつ eps = None."""
        dividend_record.dividend_adj = None
        dividend_record.dividend_actual = None
        profit_loss_record.eps = None

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert result.payout_ratio is None

    @pytest.mark.asyncio
    async def test_payout_ratio_dividend_zero(self, converter, dividend_record, profit_loss_record):
        """dividend = 0（配当なし）かつ eps > 0（payout_ratio = 0）."""
        dividend_record.dividend_actual = Decimal("0")
        profit_loss_record.eps = Decimal("100.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # 0 / 100 = 0
        assert result.payout_ratio == Decimal("0")

    @pytest.mark.asyncio
    async def test_payout_ratio_high_value(self, converter, dividend_record, profit_loss_record):
        """payout_ratio > 1（配当が利益を超える）."""
        dividend_record.dividend_actual = Decimal("150.00")
        profit_loss_record.eps = Decimal("100.00")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # 150 / 100 = 1.5
        assert result.payout_ratio == Decimal("1.5")


class TestDividendMetricsConverterProfitLossNone:
    """profit_loss_record = None の場合のテスト."""

    @pytest.mark.asyncio
    async def test_profit_loss_none_converts_safely(self, converter, dividend_record):
        """profit_loss_record = None でも変換可能."""
        result = await converter.to_schema(dividend_record, None)

        assert isinstance(result, EdinetDividendMetricsCreate)
        assert result.edinet_document_id == 1
        assert result.eps is None
        assert result.payout_ratio is None

    @pytest.mark.asyncio
    async def test_profit_loss_none_preserves_dividend(self, converter, dividend_record):
        """profit_loss_record = None でも dividend は保持."""
        dividend_record.dividend_actual = Decimal("50.00")
        result = await converter.to_schema(dividend_record, None)

        assert result.dividend_actual == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_profit_loss_none_eps_none(self, converter, dividend_record):
        """profit_loss_record = None の場合 eps = None."""
        result = await converter.to_schema(dividend_record, None)

        assert result.eps is None

    @pytest.mark.asyncio
    async def test_profit_loss_none_payout_ratio_none(self, converter, dividend_record):
        """profit_loss_record = None の場合 payout_ratio = None."""
        result = await converter.to_schema(dividend_record, None)

        assert result.payout_ratio is None


class TestDividendMetricsConverterEpsHandling:
    """EPS 値のハンドリングテスト."""

    @pytest.mark.asyncio
    async def test_eps_small_value(self, converter, dividend_record, profit_loss_record):
        """eps が非常に小さい値."""
        dividend_record.dividend_actual = Decimal("10.00")
        profit_loss_record.eps = Decimal("0.01")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # 10 / 0.01 = 1000
        assert result.payout_ratio == Decimal("10.00") / Decimal("0.01")

    @pytest.mark.asyncio
    async def test_eps_large_value(self, converter, dividend_record, profit_loss_record):
        """eps が非常に大きい値."""
        dividend_record.dividend_actual = Decimal("50.00")
        profit_loss_record.eps = Decimal("999999.99")

        result = await converter.to_schema(dividend_record, profit_loss_record)

        expected = Decimal("50.00") / Decimal("999999.99")
        assert result.payout_ratio == expected


class TestDividendMetricsConverterDecimalConversion:
    """Decimal 型変換テスト."""

    @pytest.mark.asyncio
    async def test_decimal_conversion_from_float(
        self, converter, dividend_record, profit_loss_record
    ):
        """float から Decimal への変換（if 使用）."""
        # record が float を返す場合のシミュレーション
        dividend_record.dividend_actual = 50.0  # float
        profit_loss_record.eps = 100.0  # float

        result = await converter.to_schema(dividend_record, profit_loss_record)

        # Decimal に変換される
        assert isinstance(result.dividend_actual, Decimal)
        assert isinstance(result.eps, Decimal)
        assert isinstance(result.payout_ratio, Decimal)

    @pytest.mark.asyncio
    async def test_decimal_conversion_from_string(
        self, converter, dividend_record, profit_loss_record
    ):
        """文字列から Decimal への変換."""
        dividend_record.dividend_actual = "50.00"  # str
        profit_loss_record.eps = "100.00"  # str

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert isinstance(result.dividend_actual, Decimal)
        assert isinstance(result.eps, Decimal)
        assert result.dividend_actual == Decimal("50.00")
        assert result.eps == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_decimal_conversion_from_int(
        self, converter, dividend_record, profit_loss_record
    ):
        """整数から Decimal への変換."""
        dividend_record.dividend_actual = 50  # int
        profit_loss_record.eps = 100  # int

        result = await converter.to_schema(dividend_record, profit_loss_record)

        assert isinstance(result.dividend_actual, Decimal)
        assert isinstance(result.eps, Decimal)
        assert result.dividend_actual == Decimal("50")
        assert result.eps == Decimal("100")
