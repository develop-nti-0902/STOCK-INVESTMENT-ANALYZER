"""Unit tests for DividendMetricsService.

配当メトリクス統合サービスのテスト。

テスト対象：
  - DB レコード検索フロー（dividend + profit_loss マッチング）
  - Converter との連携
  - Saver との連携
  - エラーハンドリング（P&L レコード見つからな場合）
  - ログ出力の確認
  - マッチング結果の集計（成功数・失敗数）
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.market_data.edinet import EdinetProfitAndLoss, EdinetStockDividend
from app.schemas.market_data.edinet import EdinetDividendMetricsCreate
from app.services.data_synchronization.market_data.edinet.dividend_metrics.service import (
    DividendMetricsService,
)


@pytest.fixture
def converter_mock():
    """DividendMetricsConverter モック."""
    converter = Mock()
    converter.to_schema = AsyncMock()
    return converter


@pytest.fixture
def saver_mock():
    """DividendMetricsSaver モック."""
    saver = Mock()
    saver.save_many = AsyncMock(return_value=[1, 2])
    return saver


@pytest.fixture
def dividend_repo_mock():
    """EdinetStockDividendRepository モック."""
    repo = Mock()
    repo.fetch_by_date_range = AsyncMock()
    return repo


@pytest.fixture
def profit_loss_repo_mock():
    """EdinetProfitAndLossRepository モック."""
    repo = Mock()
    repo.find_by_period = AsyncMock()
    return repo


@pytest.fixture
def metrics_repo_mock():
    """EdinetDividendMetricsRepository モック."""
    repo = Mock()
    return repo


@pytest.fixture
def service(
    converter_mock, saver_mock, dividend_repo_mock, profit_loss_repo_mock, metrics_repo_mock
):
    """DividendMetricsService インスタンス."""
    return DividendMetricsService(
        converter=converter_mock,
        saver=saver_mock,
        dividend_repo=dividend_repo_mock,
        profit_loss_repo=profit_loss_repo_mock,
        metrics_repo=metrics_repo_mock,
    )


@pytest.fixture
def sample_dividend_record():
    """サンプル dividend レコード."""
    record = Mock(spec=EdinetStockDividend)
    record.edinet_document_id = 1
    record.period_end_date = date(2025, 3, 31)
    record.fiscal_year = 2025
    record.dividend_adj = Decimal("50.00")
    record.dividend_actual = Decimal("48.00")
    record.is_consolidated = True
    record.symbol = "1234"
    return record


@pytest.fixture
def sample_profit_loss_record():
    """サンプル profit_loss レコード."""
    record = Mock(spec=EdinetProfitAndLoss)
    record.eps = Decimal("100.00")
    return record


@pytest.fixture
def sample_metrics_schema():
    """サンプル メトリクススキーマ."""
    return EdinetDividendMetricsCreate(
        edinet_document_id=1,
        period_end_date=date(2025, 3, 31),
        fiscal_year=2025,
        dividend_actual=Decimal("48.00"),
        eps=Decimal("100.00"),
        payout_ratio=Decimal("0.4800"),
    )


class TestDividendMetricsServiceBasicFlow:
    """基本的な統合フローテスト."""

    @pytest.mark.asyncio
    async def test_compute_and_save_metrics_basic_flow(
        self,
        service,
        dividend_repo_mock,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """基本フロー: DB検索 → P&L マッチング → Converter → Saver."""
        # Setup
        dividend_repo_mock.fetch_by_date_range.return_value = [sample_dividend_record]
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        # Execute
        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[sample_dividend_record],
        )

        # Verify
        assert result["total_records"] == 1
        assert result["matched_pairs"] == 1
        assert result["unmatched_count"] == 0
        assert result["saved_records"] == 1

    @pytest.mark.asyncio
    async def test_compute_and_save_metrics_calls_converter(
        self,
        service,
        dividend_repo_mock,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """compute_and_save_metrics が Converter を呼び出す."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[sample_dividend_record],
        )

        # Converter が呼ばれたか確認
        converter_mock.to_schema.assert_called_once()
        call_args = converter_mock.to_schema.call_args
        assert call_args[0][0] == sample_dividend_record
        assert call_args[0][1] == sample_profit_loss_record

    @pytest.mark.asyncio
    async def test_compute_and_save_metrics_calls_saver(
        self,
        service,
        dividend_repo_mock,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """compute_and_save_metrics が Saver を呼び出す."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[sample_dividend_record],
        )
        saver_mock.save_many.assert_called_once()
        call_args = saver_mock.save_many.call_args
        saved_records = call_args[0][0]
        assert len(saved_records) == 1
        assert saved_records[0] == sample_metrics_schema


class TestDividendMetricsServiceProfitLossMatching:
    """P&L マッチング処理テスト."""

    @pytest.mark.asyncio
    async def test_profit_loss_found_matching_succeeds(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """P&L レコード見つかる → マッチング成功."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[sample_dividend_record],
        )

        assert result["matched_pairs"] == 1
        assert result["unmatched_count"] == 0

    @pytest.mark.asyncio
    async def test_profit_loss_not_found_matching_fails(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
    ):
        """P&L レコード見つからない → マッチング失敗."""
        profit_loss_repo_mock.find_by_period.return_value = None
        saver_mock.save_many.return_value = []

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[sample_dividend_record],
        )

        # Converter は呼ばれない
        converter_mock.to_schema.assert_not_called()
        # metrics_to_save が空のため Saver は呼ばれない
        saver_mock.save_many.assert_not_called()
        assert result["matched_pairs"] == 0
        assert result["unmatched_count"] == 1
        assert result["saved_records"] == 0

    @pytest.mark.asyncio
    async def test_profit_loss_find_by_period_called_correctly(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """find_by_period が正しい引数で呼ばれる."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        await service.compute_and_save_metrics(
            sec_code="9999",
            dividend_records=[sample_dividend_record],
        )

        # find_by_period が正しい引数で呼ばれたか
        profit_loss_repo_mock.find_by_period.assert_called_once()
        call_args = profit_loss_repo_mock.find_by_period.call_args
        assert call_args[0][0] == "9999"  # sec_code
        assert call_args[0][1] == date(2025, 3, 31)  # period_end_date


class TestDividendMetricsServiceMultipleRecords:
    """複数レコード処理テスト."""

    @pytest.mark.asyncio
    async def test_multiple_dividend_records_all_matched(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
    ):
        """複数の dividend レコード × すべてマッチング成功."""
        # Setup: 3 個の dividend レコード
        dividend_records = []
        for i in range(1, 4):
            record = Mock(spec=EdinetStockDividend)
            record.edinet_document_id = i
            record.period_end_date = date(2025, 3, 31)
            record.fiscal_year = 2025
            record.dividend_adj = Decimal("50.00")
            dividend_records.append(record)

        # P&L レコードはすべて見つかる
        profit_loss_record = Mock(spec=EdinetProfitAndLoss)
        profit_loss_record.eps = Decimal("100.00")
        profit_loss_repo_mock.find_by_period.return_value = profit_loss_record

        # Converter の結果
        metrics_schema = EdinetDividendMetricsCreate(
            edinet_document_id=1,
            period_end_date=date(2025, 3, 31),
            fiscal_year=2025,
            dividend_actual=Decimal("50.00"),
            eps=Decimal("100.00"),
            payout_ratio=Decimal("0.5"),
        )
        converter_mock.to_schema.return_value = metrics_schema
        saver_mock.save_many.return_value = [1, 2, 3]

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=dividend_records,
        )

        # 検証
        assert result["total_records"] == 3
        assert result["matched_pairs"] == 3
        assert result["unmatched_count"] == 0
        assert result["saved_records"] == 3

    @pytest.mark.asyncio
    async def test_multiple_dividend_records_partial_match(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
    ):
        """複数の dividend レコード × 部分的にマッチング失敗."""
        # Setup: 3 個の dividend レコード
        dividend_records = []
        for i in range(1, 4):
            record = Mock(spec=EdinetStockDividend)
            record.edinet_document_id = i
            record.period_end_date = date(2025, 3, 31) if i < 3 else date(2024, 3, 31)
            record.fiscal_year = 2025 if i < 3 else 2024
            record.dividend_adj = Decimal("50.00")
            dividend_records.append(record)

        # P&L: 2 個は見つかる、1 個は見つからない
        profit_loss_record = Mock(spec=EdinetProfitAndLoss)
        profit_loss_record.eps = Decimal("100.00")

        def find_by_period_side_effect(sec_code, period_date):
            if period_date == date(2025, 3, 31):
                return profit_loss_record
            return None

        profit_loss_repo_mock.find_by_period.side_effect = find_by_period_side_effect

        # Converter の結果（2 個までしか呼ばれない）
        metrics_schema = EdinetDividendMetricsCreate(
            edinet_document_id=1,
            period_end_date=date(2025, 3, 31),
            fiscal_year=2025,
            dividend_actual=Decimal("50.00"),
            eps=Decimal("100.00"),
            payout_ratio=Decimal("0.5"),
        )
        converter_mock.to_schema.return_value = metrics_schema
        saver_mock.save_many.return_value = [1, 2]

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=dividend_records,
        )

        # 検証
        assert result["total_records"] == 3
        assert result["matched_pairs"] == 2
        assert result["unmatched_count"] == 1
        assert result["saved_records"] == 2

    @pytest.mark.asyncio
    async def test_no_dividend_records(
        self,
        service,
        saver_mock,
    ):
        """dividend レコードが空."""
        saver_mock.save_many.return_value = []

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[],
        )

        # 検証
        assert result["total_records"] == 0
        assert result["matched_pairs"] == 0
        assert result["unmatched_count"] == 0
        assert result["saved_records"] == 0


class TestDividendMetricsServiceErrorHandling:
    """エラーハンドリングテスト."""

    @pytest.mark.asyncio
    async def test_profit_loss_repo_error_propagates(
        self,
        service,
        profit_loss_repo_mock,
        sample_dividend_record,
    ):
        """profit_loss_repo のエラーが伝播する."""
        profit_loss_repo_mock.find_by_period.side_effect = RuntimeError("DB Error")

        with pytest.raises(RuntimeError, match="DB Error"):
            await service.compute_and_save_metrics(
                sec_code="1234",
                dividend_records=[sample_dividend_record],
            )

    @pytest.mark.asyncio
    async def test_converter_error_propagates(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        sample_dividend_record,
        sample_profit_loss_record,
    ):
        """Converter のエラーが伝播する."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.side_effect = ValueError("Conversion Error")

        with pytest.raises(ValueError, match="Conversion Error"):
            await service.compute_and_save_metrics(
                sec_code="1234",
                dividend_records=[sample_dividend_record],
            )

    @pytest.mark.asyncio
    async def test_saver_error_propagates(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """Saver のエラーが伝播する."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.side_effect = ValueError("Save Error")

        with pytest.raises(ValueError, match="Save Error"):
            await service.compute_and_save_metrics(
                sec_code="1234",
                dividend_records=[sample_dividend_record],
            )


class TestDividendMetricsServiceReturnValue:
    """戻り値検証テスト."""

    @pytest.mark.asyncio
    async def test_return_value_structure(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """戻り値が正しい構造を持つ."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=[sample_dividend_record],
        )

        # 戻り値が dict で、必要なキーを含む
        assert isinstance(result, dict)
        assert "total_records" in result
        assert "matched_pairs" in result
        assert "unmatched_count" in result
        assert "saved_records" in result

    @pytest.mark.asyncio
    async def test_return_values_sum_check(
        self,
        service,
        profit_loss_repo_mock,
        converter_mock,
        saver_mock,
        sample_dividend_record,
        sample_profit_loss_record,
        sample_metrics_schema,
    ):
        """matched_pairs + unmatched_count = total_records."""
        profit_loss_repo_mock.find_by_period.return_value = sample_profit_loss_record
        converter_mock.to_schema.return_value = sample_metrics_schema
        saver_mock.save_many.return_value = [1]

        dividend_records = [sample_dividend_record]

        result = await service.compute_and_save_metrics(
            sec_code="1234",
            dividend_records=dividend_records,
        )

        # 分割チェック
        assert result["matched_pairs"] + result["unmatched_count"] == result["total_records"]
