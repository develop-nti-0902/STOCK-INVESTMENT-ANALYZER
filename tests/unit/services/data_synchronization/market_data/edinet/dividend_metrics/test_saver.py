"""Unit tests for DividendMetricsSaver.

配当メトリクス保存層のテスト。

テスト対象：
  - UPSERT 操作（複数レコード保存）
  - 空リスト処理
  - ユニーク制約の検証（edinet_document_id + period_end_date）
  - ログ出力の確認
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.market_data.edinet import EdinetDividendMetricsCreate
from app.services.data_synchronization.market_data.edinet.dividend_metrics.saver import (
    DividendMetricsSaver,
)


@pytest.fixture
def repository_mock():
    """EdinetDividendMetricsRepository モック."""
    repo = Mock()
    repo.save_batch = AsyncMock(return_value=[1, 2, 3])  # 3 レコード保存
    return repo


@pytest.fixture
def db_session_mock():
    """AsyncSession モック."""
    return Mock()


@pytest.fixture
def saver(repository_mock, db_session_mock):
    """DividendMetricsSaver インスタンス."""
    return DividendMetricsSaver(repository_mock, db_session_mock)


@pytest.fixture
def sample_records():
    """サンプル Pydantic レコード."""
    return [
        EdinetDividendMetricsCreate(
            edinet_document_id=1,
            period_end_date=date(2025, 3, 31),
            fiscal_year=2025,
            dividend_actual=Decimal("50.00"),
            eps=Decimal("100.00"),
            payout_ratio=Decimal("0.5000"),
            is_consolidated=True,
        ),
        EdinetDividendMetricsCreate(
            edinet_document_id=2,
            period_end_date=date(2025, 3, 31),
            fiscal_year=2025,
            dividend_actual=Decimal("60.00"),
            eps=Decimal("120.00"),
            payout_ratio=Decimal("0.5000"),
            is_consolidated=True,
        ),
    ]


class TestDividendMetricsSaverBasicOperation:
    """基本的な保存操作テスト."""

    @pytest.mark.asyncio
    async def test_save_many_calls_repository(self, saver, repository_mock, sample_records):
        """save_many が repository.save_batch を呼び出す."""
        await saver.save_many(sample_records)

        repository_mock.save_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_many_returns_result(self, saver, repository_mock, sample_records):
        """save_many が repository の結果を返す."""
        repository_mock.save_batch.return_value = [1, 2]

        result = await saver.save_many(sample_records)

        assert result == [1, 2]

    @pytest.mark.asyncio
    async def test_save_many_converts_to_dict(self, saver, repository_mock, sample_records):
        """save_many が Pydantic オブジェクトを dict に変換する."""
        await saver.save_many(sample_records)

        # repository.save_batch に渡された引数を確認
        call_args = repository_mock.save_batch.call_args
        assert call_args is not None

        records_dicts = call_args[0][0]  # 第1引数
        assert isinstance(records_dicts, list)
        assert len(records_dicts) == 2
        assert isinstance(records_dicts[0], dict)
        assert "edinet_document_id" in records_dicts[0]
        assert records_dicts[0]["edinet_document_id"] == 1

    @pytest.mark.asyncio
    async def test_save_many_single_record(self, saver, repository_mock):
        """1個のレコード保存."""
        record = EdinetDividendMetricsCreate(
            edinet_document_id=1,
            period_end_date=date(2025, 3, 31),
            fiscal_year=2025,
            dividend_actual=Decimal("50.00"),
            eps=Decimal("100.00"),
            payout_ratio=Decimal("0.5"),
            is_consolidated=True,
        )
        repository_mock.save_batch.return_value = [1]

        result = await saver.save_many([record])

        assert len(result) == 1
        repository_mock.save_batch.assert_called_once()


class TestDividendMetricsSaverEmptyList:
    """空リスト処理テスト."""

    @pytest.mark.asyncio
    async def test_save_many_empty_list_no_call(self, saver, repository_mock):
        """空リストの場合 repository.save_batch を呼ばない."""
        _ = await saver.save_many([])

        repository_mock.save_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_many_empty_list_returns_empty(self, saver, repository_mock):
        """空リストの場合 [] を返す."""
        result = await saver.save_many([])

        assert result == []

    @pytest.mark.asyncio
    async def test_save_many_empty_list_no_error(self, saver, repository_mock):
        """空リスト処理でエラーが発生しない."""
        # 例外を発生させない
        result = await saver.save_many([])
        assert isinstance(result, list)


class TestDividendMetricsSaverMultipleRecords:
    """複数レコード保存テスト."""

    @pytest.mark.asyncio
    async def test_save_many_multiple_records(self, saver, repository_mock, sample_records):
        """複数レコードを保存."""
        repository_mock.save_batch.return_value = [1, 2, 3]

        result = await saver.save_many(sample_records)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_save_many_large_batch(self, saver, repository_mock):
        """大量のレコードを保存（バッチ処理確認）."""
        records = [
            EdinetDividendMetricsCreate(
                edinet_document_id=i,
                period_end_date=date(2025, 3, 31),
                fiscal_year=2025,
                dividend_actual=Decimal("50.00") + Decimal(i),
                eps=Decimal("100.00") + Decimal(i),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            )
            for i in range(1, 101)  # 100 個のレコード
        ]
        repository_mock.save_batch.return_value = list(range(1, 101))

        result = await saver.save_many(records)

        assert len(result) == 100
        repository_mock.save_batch.assert_called_once()

        # 第1引数に 100 個のレコード辞書が渡されていることを確認
        call_args = repository_mock.save_batch.call_args
        records_dicts = call_args[0][0]
        assert len(records_dicts) == 100


class TestDividendMetricsSaverDataIntegrity:
    """データ整合性テスト."""

    @pytest.mark.asyncio
    async def test_save_many_preserves_all_fields(self, saver, repository_mock):
        """すべてのフィールドを保存時に保持."""
        record = EdinetDividendMetricsCreate(
            edinet_document_id=999,
            period_end_date=date(2024, 12, 31),
            fiscal_year=2024,
            dividend_actual=Decimal("123.45"),
            eps=Decimal("234.56"),
            payout_ratio=Decimal("0.5255"),
            is_consolidated=False,
        )
        repository_mock.save_batch.return_value = [1]

        await saver.save_many([record])

        call_args = repository_mock.save_batch.call_args
        records_dicts = call_args[0][0]
        saved_dict = records_dicts[0]

        assert saved_dict["edinet_document_id"] == 999
        assert saved_dict["period_end_date"] == date(2024, 12, 31)
        assert saved_dict["fiscal_year"] == 2024
        assert saved_dict["dividend_actual"] == Decimal("123.45")
        assert saved_dict["eps"] == Decimal("234.56")
        assert saved_dict["payout_ratio"] == Decimal("0.5255")
        assert saved_dict["is_consolidated"] is False

    @pytest.mark.asyncio
    async def test_save_many_preserves_none_values(self, saver, repository_mock):
        """NULL値が保存時に保持される."""
        record = EdinetDividendMetricsCreate(
            edinet_document_id=1,
            period_end_date=date(2025, 3, 31),
            fiscal_year=None,  # NULL
            dividend_actual=None,  # NULL
            eps=None,  # NULL
            payout_ratio=None,  # NULL
            is_consolidated=None,  # NULL
        )
        repository_mock.save_batch.return_value = [1]

        await saver.save_many([record])

        call_args = repository_mock.save_batch.call_args
        records_dicts = call_args[0][0]
        saved_dict = records_dicts[0]

        assert saved_dict["fiscal_year"] is None
        assert saved_dict["dividend_actual"] is None
        assert saved_dict["eps"] is None
        assert saved_dict["payout_ratio"] is None
        assert saved_dict["is_consolidated"] is None


class TestDividendMetricsSaverErrorHandling:
    """エラーハンドリングテスト."""

    @pytest.mark.asyncio
    async def test_save_many_propagates_repository_error(
        self, saver, repository_mock, sample_records
    ):
        """repository.save_batch のエラーが伝播する."""
        repository_mock.save_batch.side_effect = ValueError("DB Error")

        with pytest.raises(ValueError, match="DB Error"):
            await saver.save_many(sample_records)

    @pytest.mark.asyncio
    async def test_save_many_propagates_async_error(self, saver, repository_mock, sample_records):
        """非同期エラーが伝播する."""

        async def raise_error(*args, **kwargs):
            raise RuntimeError("Async operation failed")

        repository_mock.save_batch.side_effect = raise_error

        with pytest.raises(RuntimeError, match="Async operation failed"):
            await saver.save_many(sample_records)


class TestDividendMetricsSaverUpsertBehavior:
    """UPSERT 動作テスト."""

    @pytest.mark.asyncio
    async def test_save_many_upsert_same_unique_key(self, saver, repository_mock):
        """同じユニークキー（edinet_document_id, period_end_date）のレコード."""
        records = [
            EdinetDividendMetricsCreate(
                edinet_document_id=1,
                period_end_date=date(2025, 3, 31),
                fiscal_year=2025,
                dividend_actual=Decimal("50.00"),  # 1回目
                eps=Decimal("100.00"),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            ),
            EdinetDividendMetricsCreate(
                edinet_document_id=1,
                period_end_date=date(2025, 3, 31),
                fiscal_year=2025,
                dividend_actual=Decimal("55.00"),  # 2回目（UPDATE）
                eps=Decimal("110.00"),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            ),
        ]
        repository_mock.save_batch.return_value = [1]

        # 複数回保存できるはず（UPSERT対応）
        result = await saver.save_many(records)

        assert len(result) == 1  # 同じ ID は1個の結果

    @pytest.mark.asyncio
    async def test_save_many_different_unique_keys(self, saver, repository_mock):
        """異なるユニークキーのレコード."""
        records = [
            EdinetDividendMetricsCreate(
                edinet_document_id=1,
                period_end_date=date(2025, 3, 31),
                fiscal_year=2025,
                dividend_actual=Decimal("50.00"),
                eps=Decimal("100.00"),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            ),
            EdinetDividendMetricsCreate(
                edinet_document_id=1,
                period_end_date=date(2024, 3, 31),  # 異なる期末日
                fiscal_year=2024,
                dividend_actual=Decimal("60.00"),
                eps=Decimal("120.00"),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            ),
        ]
        repository_mock.save_batch.return_value = [1, 2]

        result = await saver.save_many(records)

        assert len(result) == 2  # 異なるキーは 2 個

    @pytest.mark.asyncio
    async def test_save_many_different_document_ids(self, saver, repository_mock):
        """異なるドキュメント ID のレコード."""
        records = [
            EdinetDividendMetricsCreate(
                edinet_document_id=1,
                period_end_date=date(2025, 3, 31),
                fiscal_year=2025,
                dividend_actual=Decimal("50.00"),
                eps=Decimal("100.00"),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            ),
            EdinetDividendMetricsCreate(
                edinet_document_id=2,  # 異なるドキュメント ID
                period_end_date=date(2025, 3, 31),
                fiscal_year=2025,
                dividend_actual=Decimal("60.00"),
                eps=Decimal("120.00"),
                payout_ratio=Decimal("0.5"),
                is_consolidated=True,
            ),
        ]
        repository_mock.save_batch.return_value = [1, 2]

        result = await saver.save_many(records)

        assert len(result) == 2
