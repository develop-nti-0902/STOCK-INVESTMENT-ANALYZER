"""銘柄マスタモデル定義モジュール (移動済み).

元の `app.models.stock_master` から移動しました。相対インポートはパッケージ階層に合わせて調整しています。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin

# is_active カラムの値を表す定数
IS_ACTIVE = 1
IS_INACTIVE = 0


class StockMaster(SerialPKMixin, TimestampMixin, Base):
    """管理DBの `stock_master` テーブルに合わせたモデル定義.

    詳細は元ファイルの docstring を参照してください。
    """

    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    market_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sector_code_33: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    sector_name_33: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sector_code_17: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    sector_name_17: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scale_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    scale_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_date: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("idx_stock_master_code", "stock_code"),
        Index("idx_stock_master_active", "is_active"),
        Index("idx_stock_master_market", "market_category"),
        Index("idx_stock_master_sector_33", "sector_code_33"),
    )

    @property
    def symbol(self) -> str:
        """証券コード（`stock_code`）を返します."""
        return self.stock_code

    @symbol.setter
    def symbol(self, value: str) -> None:
        self.stock_code = value

    @property
    def name(self) -> str:
        """銘柄名（`stock_name`）を返します."""
        return self.stock_name

    @name.setter
    def name(self, value: str) -> None:
        self.stock_name = value

    def __repr__(self) -> str:
        """インスタンスの簡易文字列表現を返します.

        デバッグやログ出力で識別しやすい短い文字列を返します。
        """
        return "<StockMaster(stock_code=" f"{self.stock_code!r}, stock_name={self.stock_name!r})>"


__all__ = ["StockMaster"]
