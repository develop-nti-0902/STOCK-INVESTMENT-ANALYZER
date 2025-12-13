"""
StockDataRepository単体テスト

StockDataRepositoryのUPSERT処理とデータ取得機能をテストします。
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.stock_data_repository import (
    StockData1dRepository,
    StockData1hRepository,
    StockData1moRepository,
    StockData1mRepository,
    StockData1wkRepository,
    StockData5mRepository,
    StockData15mRepository,
    StockData30mRepository,
)


class TestStockDataRepository:
    """StockDataRepository基底クラスのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックDBセッション"""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def repo_1m(self, mock_session):
        """1分足Repositoryインスタンス"""
        return StockData1mRepository(mock_session)

    @pytest.fixture
    def repo_1d(self, mock_session):
        """日足Repositoryインスタンス"""
        return StockData1dRepository(mock_session)

    @pytest.mark.asyncio
    async def test_upsert_single_success_insert(self, repo_1m):
        """単一UPSERT（新規挿入）の成功"""
        # Arrange
        # テストデータ
        data = {
            "symbol": "7203.T",
            "timestamp": datetime(2024, 1, 1, 9, 0, 0),
            "open": 1500.0,
            "high": 1510.0,
            "low": 1495.0,
            "close": 1505.0,
            "volume": 1000,
        }

        # モック設定
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_result.inserted_primary_key = [1]  # 挿入成功
        repo_1m.session.execute.return_value = mock_result

        # Act
        result = await repo_1m.upsert_single(data)

        # Assert
        assert result["operation"] == "upsert"
        assert result["rowcount"] == 1
        assert result["timeframe"] == "1m"
        assert result["symbol"] == "7203.T"

        # executeが呼ばれたことを確認
        repo_1m.session.execute.assert_called_once()
        repo_1m.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_single_success_update(self, repo_1m):
        """単一UPSERT（更新）の成功"""
        # Arrange
        # テストデータ
        data = {
            "symbol": "7203.T",
            "timestamp": datetime(2024, 1, 1, 9, 0, 0),
            "open": 1500.0,
            "high": 1510.0,
            "low": 1495.0,
            "close": 1505.0,
            "volume": 1000,
        }

        # モック設定（更新の場合）
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_result.inserted_primary_key = None  # 更新成功
        repo_1m.session.execute.return_value = mock_result

        # Act
        result = await repo_1m.upsert_single(data)

        # Assert
        assert result["operation"] == "upsert"
        assert result["rowcount"] == 1

    @pytest.mark.asyncio
    async def test_upsert_single_missing_fields(self, repo_1m):
        """必須フィールド不足時のエラー"""
        # Arrange
        # 不完全なデータ
        data = {
            "symbol": "7203.T",
            # timestamp が不足
            "open": 1500.0,
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required fields"):
            await repo_1m.upsert_single(data)

    @pytest.mark.asyncio
    async def test_upsert_single_empty_data(self, repo_1m):
        """空データ時のエラー"""
        # Act & Assert
        with pytest.raises(ValueError, match="Data cannot be empty"):
            await repo_1m.upsert_single({})

    @pytest.mark.asyncio
    async def test_upsert_bulk_success(self, repo_1m):
        """一括UPSERTの成功"""
        # Arrange
        # テストデータ
        data_list = [
            {
                "symbol": "7203.T",
                "timestamp": datetime(2024, 1, 1, 9, 0, 0),
                "open": 1500.0,
                "high": 1510.0,
                "low": 1495.0,
                "close": 1505.0,
                "volume": 1000,
            },
            {
                "symbol": "7203.T",
                "timestamp": datetime(2024, 1, 1, 9, 1, 0),
                "open": 1505.0,
                "high": 1515.0,
                "low": 1500.0,
                "close": 1510.0,
                "volume": 1200,
            },
        ]

        # モック設定
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_result.inserted_primary_key = [1]
        repo_1m.session.execute.return_value = mock_result

        # Act
        result = await repo_1m.upsert_bulk(data_list)

        # Assert
        assert result == 2

    @pytest.mark.asyncio
    async def test_upsert_bulk_partial_failure(self, repo_1m):
        """一括UPSERTの部分失敗"""
        # Arrange
        # テストデータ（1つは不完全）
        data_list = [
            {
                "symbol": "7203.T",
                "timestamp": datetime(2024, 1, 1, 9, 0, 0),
                "open": 1500.0,
                "high": 1510.0,
                "low": 1495.0,
                "close": 1505.0,
                "volume": 1000,
            },
            {
                "symbol": "7203.T",
                # timestamp が不足
                "open": 1505.0,
            },
        ]

        # モック設定
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_result.inserted_primary_key = [1]
        repo_1m.session.execute.return_value = mock_result

        # Act
        result = await repo_1m.upsert_bulk(data_list)

        # Assert
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_by_symbol_and_range_1m(self, repo_1m):
        """1分足データの期間指定取得"""
        # Arrange
        # モック設定
        mock_records = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        repo_1m.session.execute.return_value = mock_result

        # Act
        start = datetime(2024, 1, 1, 9, 0, 0)
        end = datetime(2024, 1, 1, 15, 0, 0)
        result = await repo_1m.get_by_symbol_and_range("7203.T", start, end)

        # Assert
        assert result == mock_records
        repo_1m.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_symbol_and_range_1d(self, repo_1d):
        """日足データの期間指定取得"""
        # Arrange
        # モック設定
        mock_records = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        repo_1d.session.execute.return_value = mock_result

        # Act
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        result = await repo_1d.get_by_symbol_and_range("7203.T", start, end)

        # Assert
        assert result == mock_records
        repo_1d.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest(self, repo_1m):
        """最新データの取得"""
        # Arrange
        # モック設定
        mock_records = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        repo_1m.session.execute.return_value = mock_result

        # Act
        result = await repo_1m.get_latest("7203.T", limit=5)

        # Assert
        assert result == mock_records
        repo_1m.session.execute.assert_called_once()


class TestTimeframeSpecificRepositories:
    """タイムフレーム別Repositoryのテスト"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    def test_timeframe_properties(self, mock_session):
        """各Repositoryのタイムフレームプロパティ確認"""
        # Arrange
        repos = [
            (StockData1mRepository(mock_session), "1m", "timestamp"),
            (StockData5mRepository(mock_session), "5m", "timestamp"),
            (StockData15mRepository(mock_session), "15m", "timestamp"),
            (StockData30mRepository(mock_session), "30m", "timestamp"),
            (StockData1hRepository(mock_session), "1h", "timestamp"),
            (StockData1dRepository(mock_session), "1d", "date"),
            (StockData1wkRepository(mock_session), "1wk", "date"),
            (StockData1moRepository(mock_session), "1mo", "date"),
        ]

        # Act & Assert
        for repo, expected_timeframe, expected_column in repos:
            assert repo.timeframe == expected_timeframe
            assert repo.time_column == expected_column
