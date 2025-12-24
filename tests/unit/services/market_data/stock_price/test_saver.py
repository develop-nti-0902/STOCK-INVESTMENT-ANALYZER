"""
StockPriceSaverの単体テスト

StockPriceSaverの基本機能とデータ変換をテストします。
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data.stock_price.saver import StockPriceSaver


class TestStockPriceSaver:
    """StockPriceSaverのテストクラス"""

    @pytest.fixture
    def mock_session(self):
        """モックDBセッション"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def saver(self, mock_session):
        """テスト対象のSaverインスタンス"""
        return StockPriceSaver(mock_session)

    def test_init(self, mock_session):
        """初期化テスト"""
        saver = StockPriceSaver(
            mock_session, batch_size=500, max_concurrent_batches=2
        )

        assert saver.session == mock_session
        assert saver.batch_size == 500
        assert saver.max_concurrent_batches == 2
        assert len(saver.repositories) == 8  # 8種類のタイムフレーム

        # 全タイムフレームのRepositoryが初期化されていることを確認
        expected_timeframes = [
            "1m",
            "5m",
            "15m",
            "30m",
            "1h",
            "1d",
            "1wk",
            "1mo",
        ]
        for timeframe in expected_timeframes:
            assert timeframe in saver.repositories

    def test_select_repository_valid(self, saver):
        """有効なタイムフレームのRepository選択テスト"""
        repo = saver._select_repository("1d")
        assert repo is not None
        assert hasattr(repo, "upsert_bulk")

    def test_select_repository_invalid(self, saver):
        """無効なタイムフレームのRepository選択テスト"""
        repo = saver._select_repository("invalid")
        assert repo is None

    def test_convert_dataframe_to_db_records_valid(self, saver):
        """有効なDataFrameの変換テスト"""
        # テストデータ作成
        data = {
            "timestamp": ["2023-01-01 09:00:00", "2023-01-01 09:01:00"],
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [95.0, 96.0],
            "close": [102.0, 103.0],
            "volume": [1000, 1100],
        }
        df = pd.DataFrame(data)

        records = saver._convert_dataframe_to_db_records("7203", df)

        assert len(records) == 2
        assert records[0]["symbol"] == "7203"
        assert records[0]["open"] == 100.0
        assert records[0]["close"] == 102.0
        assert records[0]["volume"] == 1000
        assert isinstance(records[0]["timestamp"], datetime)

    def test_convert_dataframe_to_db_records_missing_columns(self, saver):
        """必須カラム欠如時のエラーテスト"""
        # volumeカラム欠如
        data = {
            "timestamp": ["2023-01-01 09:00:00"],
            "open": [100.0],
            "high": [105.0],
            "low": [95.0],
            "close": [102.0],
            # volumeなし
        }
        df = pd.DataFrame(data)

        with pytest.raises(ValueError, match="Missing required columns"):
            saver._convert_dataframe_to_db_records("7203", df)

    def test_convert_dict_list_to_db_records_valid(self, saver):
        """有効な辞書リストの変換テスト"""
        data_list = [
            {
                "timestamp": "2023-01-01 09:00:00",
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": 102.0,
                "volume": 1000,
            },
            {
                "timestamp": "2023-01-01 09:01:00",
                "open": 101.0,
                "high": 106.0,
                "low": 96.0,
                "close": 103.0,
                "volume": 1100,
            },
        ]

        records = saver._convert_dict_list_to_db_records("7203", data_list)

        assert len(records) == 2
        assert records[0]["symbol"] == "7203"
        assert records[1]["volume"] == 1100

    def test_prepare_data_for_db_dataframe(self, saver):
        """DataFrame形式のデータ準備テスト"""
        data = {
            "timestamp": ["2023-01-01 09:00:00"],
            "open": [100.0],
            "high": [105.0],
            "low": [95.0],
            "close": [102.0],
            "volume": [1000],
        }
        df = pd.DataFrame(data)

        records = saver._prepare_data_for_db("7203", df)

        assert len(records) == 1
        assert records[0]["symbol"] == "7203"

    def test_prepare_data_for_db_dict_list(self, saver):
        """辞書リスト形式のデータ準備テスト"""
        data_list = [
            {
                "timestamp": "2023-01-01 09:00:00",
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": 102.0,
                "volume": 1000,
            }
        ]

        records = saver._prepare_data_for_db("7203", data_list)

        assert len(records) == 1
        assert records[0]["symbol"] == "7203"

    def test_prepare_data_for_db_invalid_type(self, saver):
        """無効なデータ型のエラーテスト"""
        with pytest.raises(ValueError, match="Unsupported data type"):
            saver._prepare_data_for_db("7203", "invalid_data")

    @pytest.mark.asyncio
    async def test_save_stock_data_success(self, saver, mock_session):
        """株価データ保存成功テスト"""
        # モックRepositoryの設定
        mock_repo = AsyncMock()
        mock_repo.upsert_bulk.return_value = 1
        saver.repositories["1d"] = mock_repo

        # テストデータ
        data = {
            "timestamp": ["2023-01-01 09:00:00"],
            "open": [100.0],
            "high": [105.0],
            "low": [95.0],
            "close": [102.0],
            "volume": [1000],
        }
        df = pd.DataFrame(data)

        result = await saver.save_single_stock_data("7203", "1d", df)

        assert result is True
        mock_repo.upsert_bulk.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_stock_data_invalid_timeframe(self, saver):
        """無効なタイムフレームのエラーテスト"""
        data = {
            "timestamp": ["2023-01-01 09:00:00"],
            "open": [100.0],
            "high": [105.0],
            "low": [95.0],
            "close": [102.0],
            "volume": [1000],
        }
        df = pd.DataFrame(data)

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            await saver.save_single_stock_data("7203", "invalid", df)

    @pytest.mark.asyncio
    async def test_save_multiple_stocks(self, saver, mock_session):
        """複数銘柄保存テスト"""
        from unittest.mock import AsyncMock, patch

        # モックRepositoryの設定
        mock_repo_1d = AsyncMock()
        mock_repo_1d.upsert_bulk.return_value = 1  # 1件のデータなので1を返す
        mock_repo_1h = AsyncMock()
        mock_repo_1h.upsert_bulk.return_value = 1

        saver.repositories["1d"] = mock_repo_1d
        saver.repositories["1h"] = mock_repo_1h

        # get_session_maker をモックして、独自セッション作成を回避
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_maker():
            # モックセッションを返す
            mock_sess = AsyncMock()
            mock_sess.commit = AsyncMock()
            mock_sess.rollback = AsyncMock()
            try:
                yield mock_sess
            finally:
                pass

        # テストデータ
        data_dict = {
            "7203": {
                "1d": [
                    {
                        "timestamp": "2023-01-01",
                        "open": 100.0,
                        "high": 105.0,
                        "low": 95.0,
                        "close": 102.0,
                        "volume": 1000,
                    }
                ],
                "1h": [
                    {
                        "timestamp": "2023-01-01 09:00:00",
                        "open": 100.0,
                        "high": 105.0,
                        "low": 95.0,
                        "close": 102.0,
                        "volume": 1000,
                    }
                ],
            },
            "9984": {
                "1d": [
                    {
                        "timestamp": "2023-01-01",
                        "open": 200.0,
                        "high": 205.0,
                        "low": 195.0,
                        "close": 202.0,
                        "volume": 2000,
                    }
                ],
            },
        }

        # get_session_makerをパッチして、_save_single_stock_asyncが独自セッションを作らないようにする
        with patch(
            "app.services.market_data.stock_price.saver.get_session_maker",
            return_value=mock_session_maker,
        ):
            results = await saver.save_batch_stocks(data_dict)

        assert "7203_1d" in results
        assert "7203_1h" in results
        assert "9984_1d" in results
        assert results["7203_1d"] == 1
        assert results["7203_1h"] == 1
        assert results["9984_1d"] == 1

    def test_save_base_saver_interface(self, saver):
        """BaseSaverインターフェースのテスト"""
        # saveメソッドの存在確認
        assert hasattr(saver, "save")
        assert hasattr(saver, "save_batch")

    @pytest.mark.asyncio
    async def test_save_batch_base_interface(self, saver, mock_session):
        """BaseSaverのsave_batchインターフェーステスト"""
        # モックRepositoryの設定
        mock_repo = AsyncMock()
        mock_repo.upsert_bulk.return_value = 2
        saver.repositories["1d"] = mock_repo

        # BaseSaver形式のデータ
        data_list = [
            {
                "symbol": "7203",
                "timeframe": "1d",
                "records": [
                    {
                        "timestamp": "2023-01-01",
                        "open": 100.0,
                        "high": 105.0,
                        "low": 95.0,
                        "close": 102.0,
                        "volume": 1000,
                    }
                ],
            }
        ]

        # 内部で並列処理やセッション生成が行われるため、
        # 集計部分だけをテストするために save_batch_stocks をモック化する
        saver.save_batch_stocks = AsyncMock(return_value={"7203_1d": 2})

        result = await saver.save_batch(data_list)

        # 集計が期待どおりに行われることを検証
        assert result == 2
