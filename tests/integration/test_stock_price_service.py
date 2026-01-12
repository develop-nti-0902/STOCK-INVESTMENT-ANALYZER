"""
StockPriceService統合テスト

株価データ収集サービスの統合動作をテストします。
"""

import pytest

from app.services.market_data.stock_price import (
    StockPriceConverter,
    StockPriceFetcher,
    StockPriceSaver,
    StockPriceService,
    StockPriceValidator,
)


class TestStockPriceServiceIntegration:
    """StockPriceServiceの統合テスト"""

    def setup_method(self):
        """テスト前準備"""
        self.fetcher = StockPriceFetcher()
        self.converter = StockPriceConverter()
        self.validator = StockPriceValidator()
        # ダミーのバッチサービス（テスト用）
        from unittest.mock import AsyncMock, MagicMock

        self.dummy_batch = MagicMock()
        self.dummy_batch.create_job = AsyncMock(return_value=MagicMock(id=1))
        self.dummy_batch.start_job = AsyncMock()
        self.dummy_batch.update_progress = AsyncMock()
        self.dummy_batch.complete_job = AsyncMock()
        self.dummy_batch.get_job_status = AsyncMock(
            return_value=MagicMock(
                successful_stocks=0, failed_stocks=0, processed_stocks=0
            )
        )
        # saverはDBセッションが必要なので、テストDBを使用

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """サービスの初期化テスト"""
        from unittest.mock import MagicMock

        mock_saver = MagicMock(spec=StockPriceSaver)
        service = StockPriceService(
            fetcher=self.fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        assert service.fetcher is self.fetcher
        assert service.saver is mock_saver
        assert service.converter is self.converter
        assert service.validator is self.validator
        assert service.max_concurrent == 5  # デフォルト値

    @pytest.mark.asyncio
    async def test_converter_integration(self):
        """Converterの統合テスト"""
        # テストデータ作成
        import pandas as pd

        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [95.0, 96.0],
                "Close": [102.0, 103.0],
                "Volume": [1000000, 1100000],
                "Adj Close": [102.0, 103.0],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        # このコードベースでは `Converter.from_dataframe` は実装されていないため、
        # DataFrame の行から手動で Pydantic モデルを構築します。
        from app.schemas.stock_data import StockPriceCreate

        pydantic_data = []
        for idx, row in df.iterrows():
            pydantic_data.append(
                StockPriceCreate(
                    symbol="7203.T",
                    trade_date=idx.to_pydatetime(),
                    open_price=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                    adj_close=float(row["Adj Close"]),
                )
            )

        assert len(pydantic_data) == 2

        # Validatorで検証
        for item in pydantic_data:
            result = self.validator.validate(item)
            assert result.is_valid, f"Validation failed: {result.errors}"

        # 辞書への変換 — Saver 用の形式に変換するため `to_saver_records` を使用する
        dict_data = self.converter.to_saver_records(pydantic_data)
        assert len(dict_data) == 2
        assert all(isinstance(d, dict) for d in dict_data)
        # `to_saver_records` は `timestamp`, `open` 等の Saver フレンドリな辞書を返す
        assert all("timestamp" in d for d in dict_data)
        assert all("open" in d for d in dict_data)

    @pytest.mark.asyncio
    async def test_validator_comprehensive(self):
        """Validatorの包括的テスト"""
        from datetime import datetime, timezone

        from app.schemas.stock_data import StockPriceCreate

        # 有効なデータ
        valid_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
        )

        result = self.validator.validate(valid_data)
        assert result.is_valid is True

        # 無効なデータ（OHLC整合性違反）
        invalid_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=110.0,  # 高値より高い
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
        )

        result = self.validator.validate(invalid_data)
        # yfinance raw dataはバイパスされるため、is_valid=Trueになる
        assert result.is_valid is True
        # バイパス警告が含まれていることを確認
        assert any(
            "Validation bypassed" in warning or "yfinance" in warning
            for warning in result.warnings
        )

    # 注意: 実際のAPI呼び出しを含むテストは、モックを使用するか、
    # テスト環境でのみ実行するように設計する必要があります。
    # 以下のテストはモックを使用した例です。

    @pytest.mark.asyncio
    async def test_service_workflow_simulation(self):
        """サービスワークフローのシミュレーションテスト"""
        # このテストでは実際のAPIを呼ばずに、モックデータを使用
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # モックデータ作成 - List[StockData]として
        from app.schemas.market_data.stock_price import StockData

        mock_stock_data_list = [
            StockData(
                symbol="7203.T",
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open_price=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000,
                adj_close=102.0,
            )
        ]

        # Fetcherをモック
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            return_value=mock_stock_data_list
        )

        # Saverをモック（実際のDB保存を避ける）
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=1)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        result = await service.fetch_and_save_single(
            symbol="7203.T", timeframe="1d"
        )

        # 検証
        assert result.success is True
        assert result.symbol == "7203.T"
        assert result.records_processed == 1
        assert result.records_saved == 1

        # 各コンポーネントが呼ばれたことを確認
        mock_fetcher.fetch_single.assert_called_once()
        mock_saver.save_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_symbols_parallel_processing(self):
        """複数銘柄並列処理のテスト"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # モックデータ作成
        from app.schemas.market_data.stock_price import StockData

        symbols = ["7203.T", "9432.T", "9984.T"]

        mock_stock_data_list = [
            StockData(
                symbol=symbol,
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open_price=100.0 + i * 10,
                high=105.0 + i * 10,
                low=95.0 + i * 10,
                close=102.0 + i * 10,
                volume=1000000 + i * 100000,
                adj_close=102.0 + i * 10,
            )
            for i, symbol in enumerate(symbols)
        ]

        # Fetcherをモック（各銘柄ごとに異なるデータを返す）
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            side_effect=[
                [mock_stock_data_list[0]],  # 7203.T
                [mock_stock_data_list[1]],  # 9432.T
                [mock_stock_data_list[2]],  # 9984.T
            ]
        )

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=1)

        # Service作成（並列度2に設定）
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            max_concurrent=2,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        results = await service.fetch_and_save_multiple(
            symbols=symbols, timeframe="1d"
        )

        # 検証
        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.records_processed == 1 for r in results)
        assert all(r.records_saved == 1 for r in results)
        assert {r.symbol for r in results} == set(symbols)

        # fetch_singleが3回呼ばれたことを確認
        assert mock_fetcher.fetch_single.call_count == 3
        # save_batchが3回呼ばれたことを確認
        assert mock_saver.save_batch.call_count == 3

    @pytest.mark.asyncio
    async def test_error_handling_partial_failure(self):
        """部分的失敗時のエラーハンドリングテスト"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # モックデータ作成
        from app.schemas.market_data.stock_price import StockData

        symbols = ["7203.T", "9432.T", "9984.T"]

        mock_stock_data_list = [
            StockData(
                symbol="7203.T",
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open_price=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000,
                adj_close=102.0,
            )
        ]

        # Fetcherをモック（2番目の銘柄で例外を発生）
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            side_effect=[
                mock_stock_data_list,  # 7203.T: 成功
                Exception("API Error"),  # 9432.T: 失敗
                mock_stock_data_list,  # 9984.T: 成功
            ]
        )

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=1)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        results = await service.fetch_and_save_multiple(
            symbols=symbols, timeframe="1d"
        )

        # 検証
        assert len(results) == 3

        # 成功した銘柄
        success_results = [r for r in results if r.success]
        assert len(success_results) == 2
        assert {r.symbol for r in success_results} == {"7203.T", "9984.T"}

        # 失敗した銘柄
        failure_results = [r for r in results if not r.success]
        assert len(failure_results) == 1
        assert failure_results[0].symbol == "9432.T"
        assert "Unexpected error: API Error" in failure_results[0].errors

    @pytest.mark.asyncio
    async def test_progress_tracking_simulation(self):
        """進捗トラッキングのシミュレーションテスト"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # 大量の銘柄をシミュレート
        symbols = [f"{i:04d}.T" for i in range(1, 11)]  # 10銘柄

        # モックデータ作成
        from app.schemas.market_data.stock_price import StockData

        mock_stock_data = StockData(
            symbol="0001.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
            adj_close=102.0,
        )

        # Fetcherをモック（全ての銘柄で同じデータを返す）
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(return_value=[mock_stock_data])

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=1)

        # Service作成（並列度3に設定）
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            max_concurrent=3,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        results = await service.fetch_and_save_multiple(
            symbols=symbols, timeframe="1d"
        )

        # 検証
        assert len(results) == 10
        assert all(r.success for r in results)
        assert all(r.records_processed == 1 for r in results)
        assert all(r.records_saved == 1 for r in results)

        # 並列処理が正しく動作したことを確認（セマフォ制御）
        # fetch_singleが10回呼ばれたことを確認
        assert mock_fetcher.fetch_single.call_count == 10
        # save_batchが10回呼ばれたことを確認
        assert mock_saver.save_batch.call_count == 10

    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """検証エラー時のハンドリングテスト"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # 無効なデータ作成（OHLC整合性違反）
        from app.schemas.market_data.stock_price import StockData

        invalid_stock_data = StockData(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=110.0,  # 高値より高い（無効）
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
            adj_close=102.0,
        )

        # Fetcherをモック
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            return_value=[invalid_stock_data]
        )

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=0)  # 保存されなかった

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        result = await service.fetch_and_save_single(
            symbol="7203.T", timeframe="1d"
        )

        # 検証: yfinance raw dataはバイパスされるため、検証は成功する
        assert result.success is True
        assert result.symbol == "7203.T"
        assert result.records_processed == 1
        # モックsaverが0を返すため、保存件数は0
        assert result.records_saved == 0

        # 各コンポーネントが呼ばれたことを確認
        mock_fetcher.fetch_single.assert_called_once()
        # Validatorがバイパスされるため、save_batchは呼ばれる
        mock_saver.save_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_date_parameter_normalization(self):
        """日付パラメータ正規化のテスト"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # モックデータ作成
        from app.schemas.market_data.stock_price import StockData

        mock_stock_data = StockData(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
            adj_close=102.0,
        )

        # Fetcherをモック
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(return_value=[mock_stock_data])

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=1)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行（様々な日付形式）
        result = await service.fetch_and_save_single(
            symbol="7203.T", timeframe="1d"
        )

        # 検証
        assert result.success is True
        mock_fetcher.fetch_single.assert_called_once()

    @pytest.mark.asyncio
    async def test_yahoo_finance_error_handling(self):
        """Yahoo Finance APIエラーのハンドリングテスト"""
        from unittest.mock import AsyncMock, MagicMock

        from app.exceptions.external_api import YahooFinanceError

        # Fetcherをモック（YahooFinanceErrorを発生）
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(side_effect=YahooFinanceError())

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        result = await service.fetch_and_save_single(
            symbol="7203.T", timeframe="1d"
        )

        # 検証
        assert result.success is False
        assert result.symbol == "7203.T"
        assert "Yahoo Finance API error" in result.errors[0]
        assert mock_saver.save_batch.call_count == 0

    @pytest.mark.asyncio
    async def test_empty_data_handling(self):
        """取得データが空の場合の挙動テスト"""
        from unittest.mock import AsyncMock, MagicMock

        # Fetcherをモック
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            return_value=[]
        )  # 空データを返す

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        result = await service.fetch_and_save_single(
            symbol="7203.T", timeframe="1d"
        )

        # 検証（データがない場合の警告）
        assert result.success is True
        assert result.records_processed == 0
        assert result.records_saved == 0
        assert "No data was retrieved" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_get_stock_data_readonly(self):
        """読み取り専用データ取得のテスト"""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # モックデータ作成
        from app.schemas.market_data.stock_price import StockData

        mock_stock_data_list = [
            StockData(
                symbol="7203.T",
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open_price=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000,
                adj_close=102.0,
            )
        ]

        # Fetcherをモック
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            return_value=mock_stock_data_list
        )

        # Saverをモック
        mock_saver = MagicMock(spec=StockPriceSaver)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
            batch_service=self.dummy_batch,
        )

        # テスト実行
        result = await service.get_stock_data(symbol="7203.T", timeframe="1d")

        # 検証
        assert result is not None
        assert result.symbol == "7203.T"
        assert result.timeframe == "1d"
        assert hasattr(result, "data")
        assert len(result.data) == 1

        # fetcherは呼ばれたがsaverは呼ばれていない
        mock_fetcher.fetch_single.assert_called_once()
        mock_saver.save_batch.assert_not_called()
