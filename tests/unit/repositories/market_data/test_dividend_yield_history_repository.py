"""DividendYieldHistoryRepository単体テスト.

配当利回り履歴リポジトリのUPSERT、取得、削除などのメソッドをテスト。
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.market_data.dividend_yield_history_repository import (
    DividendYieldHistoryRepository,
)


@pytest.fixture
def mock_session():
    """モックDBセッション."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    """DividendYieldHistoryRepositoryインスタンス."""
    return DividendYieldHistoryRepository(mock_session)


class TestDividendYieldHistoryRepository:
    """DividendYieldHistoryRepositoryのテスト."""

    @pytest.mark.asyncio
    async def test_bulk_upsert_empty_records(self, repo):
        """空レコード時は0を返す."""
        # Act
        result = await repo.bulk_upsert([])

        # Assert
        assert result == 0
        repo.session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_upsert_success(self, repo):
        """複数レコードのUPSERTが成功."""
        # Arrange
        records = [
            {
                "symbol": "7203.T",
                "date": date(2024, 1, 1),
                "dividend": Decimal("50.00"),
                "stock_price": Decimal("1500.00"),
                "dividend_yield": Decimal("0.0333"),
                "fiscal_year": 2023,
                "edinet_document_id": 1,
            },
            {
                "symbol": "9984.T",
                "date": date(2024, 1, 1),
                "dividend": Decimal("100.00"),
                "stock_price": Decimal("3000.00"),
                "dividend_yield": Decimal("0.0333"),
                "fiscal_year": 2023,
                "edinet_document_id": 2,
            },
        ]

        # モック設定
        mock_result = MagicMock()
        mock_result.rowcount = 2
        repo.session.execute.return_value = mock_result

        # Act
        result = await repo.bulk_upsert(records)

        # Assert
        assert result == 2
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_with_conflict(self, repo):
        """既存レコードの更新（UPSERT）が成功."""
        # Arrange
        records = [
            {
                "symbol": "7203.T",
                "date": date(2024, 1, 1),
                "dividend": Decimal("50.00"),
                "stock_price": Decimal("1500.00"),
                "dividend_yield": Decimal("0.0333"),
                "fiscal_year": 2023,
                "edinet_document_id": 1,
            },
        ]

        # モック設定（UPSERTで更新）
        mock_result = MagicMock()
        mock_result.rowcount = 1
        repo.session.execute.return_value = mock_result

        # Act
        result = await repo.bulk_upsert(records)

        # Assert
        # UPSERTの結果を確認
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_by_symbol_date_range_success(self, repo):
        """指定銘柄・期間のレコードを取得."""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # モック設定
        mock_result1 = MagicMock(
            symbol="7203.T",
            date=date(2024, 1, 1),
            dividend=Decimal("50.00"),
            stock_price=Decimal("1500.00"),
            dividend_yield=Decimal("0.0333"),
            fiscal_year=2023,
            edinet_document_id=1,
        )
        mock_result2 = MagicMock(
            symbol="7203.T",
            date=date(2024, 1, 15),
            dividend=Decimal("50.00"),
            stock_price=Decimal("1510.00"),
            dividend_yield=Decimal("0.0331"),
            fiscal_year=2023,
            edinet_document_id=1,
        )

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_result1, mock_result2]
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        repo.session.execute.return_value = mock_query_result

        # Act
        results = await repo.get_by_symbol_date_range("7203.T", start_date, end_date)

        # Assert
        assert len(results) == 2
        assert results[0].date == date(2024, 1, 1)
        assert results[1].date == date(2024, 1, 15)
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_symbol_date_range_empty(self, repo):
        """指定条件がない場合は空リストを返す."""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # モック設定（結果なし）
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        repo.session.execute.return_value = mock_query_result

        # Act
        results = await repo.get_by_symbol_date_range("7203.T", start_date, end_date)

        # Assert
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_by_date_range_success(self, repo):
        """指定期間のレコード削除が成功."""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # モック設定
        mock_result = MagicMock()
        mock_result.rowcount = 10
        repo.session.execute.return_value = mock_result

        # Act
        result = await repo.delete_by_date_range(start_date, end_date)

        # Assert
        assert result == 10
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_date_range_empty(self, repo):
        """削除対象がない場合は0を返す."""
        # Arrange
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # モック設定（削除数0）
        mock_result = MagicMock()
        mock_result.rowcount = 0
        repo.session.execute.return_value = mock_result

        # Act
        result = await repo.delete_by_date_range(start_date, end_date)

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_upsert_exceeds_chunk_size(self, repo):
        """チャンクサイズを超える件数でもチャンク分割してupsertされること."""
        from app.repositories.market_data.dividend_yield_history_repository import (
            _UPSERT_CHUNK_SIZE,
        )

        mock_result = MagicMock()
        mock_result.rowcount = None  # len(chunk) フォールバックを使用
        repo.session.execute.return_value = mock_result

        records = [
            {
                "symbol": f"T{i:04d}",
                "date": date(2024, 1, 1),
                "dividend": Decimal("50.00"),
                "stock_price": Decimal("1500.00"),
                "dividend_yield": Decimal("0.0333"),
                "fiscal_year": 2023,
                "edinet_document_id": i + 1,
            }
            for i in range(_UPSERT_CHUNK_SIZE + 1)
        ]

        result = await repo.bulk_upsert(records)

        # 2501件 → 2チャンクに分割、execute が2回呼ばれる
        assert repo.session.execute.call_count == 2
        assert result == _UPSERT_CHUNK_SIZE + 1


__all__ = []
