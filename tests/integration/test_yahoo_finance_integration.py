"""Yahoo Finance API統合テスト

実際のYahoo Finance APIへの接続をテストします。
ネットワーク接続が必要なため、CIではスキップされる可能性があります。
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.schemas.market_data.stock_price import StockData
from app.services.market_data.stock_price.fetcher import StockPriceFetcher


class TestYahooFinanceIntegration:
    """Yahoo Finance API統合テスト"""

    artifacts_dir = Path(__file__).parent / "artifacts"

    def _save_artifacts(self, data, test_name, symbol=None, timeframe=None):
        """テストデータをartifactsとして保存"""
        self.artifacts_dir.mkdir(exist_ok=True)

        timestamp = date.today().strftime("%Y%m%d")
        filename_parts = [test_name, timestamp]
        if symbol:
            filename_parts.append(symbol)
        if timeframe:
            filename_parts.append(timeframe)

        filename = "_".join(filename_parts) + ".json"
        filepath = self.artifacts_dir / filename

        # StockDataをdictに変換
        if isinstance(data, list):
            serializable_data = [item.model_dump() for item in data]
        elif isinstance(data, dict):
            serializable_data = {
                k: [item.model_dump() for item in v] for k, v in data.items()
            }
        else:
            serializable_data = data

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2, default=str)

        print(f"Artifacts saved to: {filepath}")

    @pytest.fixture
    def fetcher(self):
        """StockPriceFetcherインスタンスを提供"""
        return StockPriceFetcher()

    @pytest.mark.asyncio
    async def test_fetch_single_real_symbol(self, fetcher):
        """実際の銘柄シンボルで単一データ取得をテスト

        テスト用に安定した銘柄（例: トヨタ自動車）を使用
        """
        # Arrange
        symbol = "7203.T"  # トヨタ自動車
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # 過去30日分

        # Act
        result = await fetcher.fetch_single(
            symbol=symbol,
            timeframe="1d",
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0, "データが空です"
        assert all(
            isinstance(item, StockData) for item in result
        ), "StockDataオブジェクトのリストであるべき"

        # データの基本構造確認（最初のデータで確認）
        first_item = result[0]
        assert hasattr(first_item, "symbol"), "symbol属性がありません"
        assert hasattr(first_item, "trade_date"), "trade_date属性がありません"
        assert hasattr(first_item, "open_price"), "open_price属性がありません"
        assert hasattr(first_item, "close"), "close属性がありません"
        assert hasattr(first_item, "volume"), "volume属性がありません"

        # Artifactsとしてデータを保存
        self._save_artifacts(result, "fetch_single_real_symbol", symbol, "1d")

    @pytest.mark.asyncio
    async def test_fetch_multiple_real_symbols(self, fetcher):
        """実際の複数銘柄で並列データ取得をテスト"""
        # Arrange
        symbols = [
            "7203.T",
            "6758.T",
            "7974.T",
        ]  # トヨタ自動車、ソニー、任天堂
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # 過去30日分に変更

        # Act
        results = await fetcher.fetch_batch(
            symbols=symbols,
            timeframe="1d",
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        assert isinstance(results, dict)
        assert len(results) > 0, "結果が空です"

        # 少なくとも1つの銘柄がデータを持っていることを確認
        data_found = False
        for symbol in symbols:
            if symbol in results:
                data_list = results[symbol]
                assert isinstance(
                    data_list, list
                ), f"{symbol}のデータがリストであるべき"
                if len(data_list) > 0:
                    data_found = True
                    assert all(
                        isinstance(item, StockData) for item in data_list
                    ), f"{symbol}のデータがStockDataのリストであるべき"

        assert data_found, "少なくとも1つの銘柄でデータが取得できるべき"

        # Artifactsとしてデータを保存
        self._save_artifacts(
            results, "fetch_multiple_real_symbols", "_".join(symbols), "1d"
        )

    @pytest.mark.asyncio
    async def test_fetch_different_timeframes(self, fetcher):
        """異なるタイムフレームでのデータ取得をテスト"""
        # Arrange
        symbol = "9432.T"  # 日本電信電話株式会社 (NTT)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # 過去30日に変更
        timeframes = ["1d", "1wk"]

        for timeframe in timeframes:
            # Act
            result = await fetcher.fetch_single(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )

            # Assert
            assert isinstance(result, list)
            assert len(result) > 0, f"{timeframe}のデータが空です"
            assert all(
                isinstance(item, StockData) for item in result
            ), f"{timeframe}のデータがStockDataのリストであるべき"

            # Artifactsとしてデータを保存
            self._save_artifacts(
                result, "fetch_different_timeframes", symbol, timeframe
            )

    @pytest.mark.asyncio
    async def test_fetch_invalid_symbol(self, fetcher):
        """無効な銘柄シンボルでのエラーハンドリングをテスト"""
        # Arrange
        invalid_symbol = "INVALID_SYMBOL_12345"
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        # Act
        result = await fetcher.fetch_single(
            symbol=invalid_symbol,
            timeframe="1d",
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0, "無効なシンボルでは空のリストが返されるべき"

        # Artifactsとしてデータを保存（空のリスト）
        self._save_artifacts(
            result, "fetch_invalid_symbol", invalid_symbol, "1d"
        )

    @pytest.mark.asyncio
    async def test_fetch_large_date_range(self, fetcher):
        """大きな日付範囲でのデータ取得をテスト"""
        # Arrange
        symbol = "7203.T"  # トヨタ自動車
        end_date = date.today()
        start_date = end_date - timedelta(days=365)  # 過去1年

        # Act
        result = await fetcher.fetch_single(
            symbol=symbol,
            timeframe="1wk",  # 週足でまとめる
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0, "大規模データ取得でデータが空です"
        # 1年分の週足データとして、少なくとも40週分以上あるはず
        assert len(result) >= 40, f"データ行数が不足: {len(result)}行"
        assert all(
            isinstance(item, StockData) for item in result
        ), "StockDataオブジェクトのリストであるべき"

        # Artifactsとしてデータを保存
        self._save_artifacts(result, "fetch_large_date_range", symbol, "1wk")
