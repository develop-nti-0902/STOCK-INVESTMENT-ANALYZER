"""ビュー関連のスキーマ定義.

最新株価ビューのスキーマは既存の株価スキーマを継承して定義します。
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schemas.stock_data import StockPrice1D


class LatestStockBase(StockPrice1D):
    """latest_stocks_1dビューの基本スキーマ。

    `StockPrice1D` を継承して共通定義を再利用します。
    """

    model_config = ConfigDict(from_attributes=True)


class LatestStockResponse(LatestStockBase):
    """latest_stocks_1dビューのレスポンススキーマ."""

    id: int = Field(..., description="レコードID")


__all__ = ["LatestStockBase", "LatestStockResponse"]
