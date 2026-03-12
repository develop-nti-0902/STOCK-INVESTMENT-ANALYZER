"""DividendYieldMonitoring モデルのメタ情報を検証するためのテストモジュール。"""

from app.models.monitoring.dividend_yield_monitoring import DividendYieldMonitoring


def test_model_tablename() -> None:
    """__tablename__ が想定どおりであることを確かめる。"""
    assert DividendYieldMonitoring.__tablename__ == "dividend_yield_monitoring"


def test_model_columns_include_expected_fields() -> None:
    """主要フィールドがテーブル定義に含まれていることを確認する。"""
    columns = {col.name for col in DividendYieldMonitoring.__table__.columns}
    assert "symbol" in columns
    assert "monitoring_date" in columns
    assert "dividend_yield" in columns
