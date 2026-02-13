"""StockPriceConverter 単体テスト（現行実装向け）.

このテストは現在の `StockPriceConverter` 実装に合わせ、
実装済みの機能（`to_saver_records` / `_to_saver_record`）を検証し、
未実装のAPIが `NotImplementedError` を送出することを確認します.
"""

from datetime import datetime, timezone

import pytest

from app.schemas.stock_data import StockPriceCreate
from app.services.market_data.stock_price.converter import StockPriceConverter


class TestStockPriceConverter:
    """`StockPriceConverter` の振る舞いを検証するテスト群."""

    @pytest.fixture
    def converter(self) -> StockPriceConverter:
        """テスト対象インスタンスを返すフィクスチャ."""
        return StockPriceConverter()

    @pytest.fixture
    def sample_model(self) -> StockPriceCreate:
        """保存用の Pydantic モデルサンプル（UTCタイムゾーン付き）."""
        return StockPriceCreate(
            symbol="7203.T",
            timestamp=datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000,
            adj_close=102.0,
        )

    def test__to_saver_record_converts_fields_correctly(self, converter, sample_model):
        """`_to_saver_record` が期待するキーと値に変換することを検証する."""
        record = converter._to_saver_record(sample_model)

        assert record["timestamp"] == sample_model.timestamp
        assert record["open"] == sample_model.open_price
        assert record["high"] == sample_model.high
        assert record["low"] == sample_model.low
        assert record["close"] == sample_model.close
        assert record["volume"] == sample_model.volume
        assert record["adj_close"] == sample_model.adj_close

    def test_to_saver_records_converts_list(self, converter, sample_model):
        """`to_saver_records` がリストの各モデルを辞書に変換することを検証する."""
        models = [sample_model, sample_model]
        records = converter.to_saver_records(models)

        assert isinstance(records, list)
        assert len(records) == 2
        # 全要素が個別に変換されていること
        assert records[0] == converter._to_saver_record(sample_model)
        assert records[1] == converter._to_saver_record(sample_model)

    def test_unimplemented_methods_raise(self, converter):
        """未実装のAPIが `NotImplementedError` を送出することを確認する."""
        with pytest.raises(NotImplementedError):
            converter.to_pydantic({})

        with pytest.raises(NotImplementedError):
            # `timestamp` フィールド名が使用されている環境もあるため `timestamp` で作成
            converter.from_pydantic(
                StockPriceCreate(
                    symbol="X",
                    timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                    open_price=1.0,
                    high=1.0,
                    low=1.0,
                    close=1.0,
                    volume=1,
                    adj_close=1.0,
                )
            )

        with pytest.raises(NotImplementedError):
            converter.from_dataframe(None)
