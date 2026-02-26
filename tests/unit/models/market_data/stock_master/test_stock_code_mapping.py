"""StockCodeMapping モデルケテスト."""

from app.models import StockCodeMapping


class TestStockCodeMapping:
    """StockCodeMapping モデルの単体テスト."""

    def test_create_stock_code_mapping(self) -> None:
        """StockCodeMapping インスタンスの作成をテストします."""
        mapping = StockCodeMapping(stock_code="7203", sec_code="E00009001")

        assert mapping.stock_code == "7203"
        assert mapping.sec_code == "E00009001"

    def test_stock_code_mapping_repr(self) -> None:
        """StockCodeMapping の __repr__ をテストします."""
        mapping = StockCodeMapping(stock_code="7203", sec_code="E00009001")
        repr_str = repr(mapping)

        assert "StockCodeMapping" in repr_str
        assert "7203" in repr_str
        assert "E00009001" in repr_str

    def test_stock_code_mapping_table_name(self) -> None:
        """StockCodeMapping のテーブル名をテストします."""
        assert StockCodeMapping.__tablename__ == "stock_code_mapping"
