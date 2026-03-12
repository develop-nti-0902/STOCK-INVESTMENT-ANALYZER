"""銘柄マスタモデル定義モジュール (移動済み).

元の `app.models.stock_master` から移動しました。相対インポートはパッケージ階層に合わせて調整しています。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.core.base import Base, SerialPKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.market_data.stock_master.market_category_master import MarketCategoryMaster
    from app.models.market_data.stock_master.scale_master import ScaleMaster
    from app.models.market_data.stock_master.sector_17_master import Sector17Master
    from app.models.market_data.stock_master.sector_33_master import Sector33Master

# is_active カラムの値を表す定数
IS_ACTIVE = 1
IS_INACTIVE = 0


class StockMaster(SerialPKMixin, TimestampMixin, Base):
    """管理DBの `stock_master` テーブルに合わせたモデル定義.

    詳細は元ファイルの docstring を参照してください。
    """

    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # ✨ FK カラム（新規）
    market_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("market_category_master.id"), nullable=True
    )
    sector_33_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sector_33_master.id"), nullable=True
    )
    sector_17_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sector_17_master.id"), nullable=True
    )
    scale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scale_master.id"), nullable=True)

    data_date: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ✨ Relationships（新規）
    market_category: Mapped[Optional["MarketCategoryMaster"]] = relationship(
        "MarketCategoryMaster", lazy="select"
    )
    sector_33: Mapped[Optional["Sector33Master"]] = relationship("Sector33Master", lazy="select")
    sector_17: Mapped[Optional["Sector17Master"]] = relationship("Sector17Master", lazy="select")
    scale: Mapped[Optional["ScaleMaster"]] = relationship("ScaleMaster", lazy="select")

    __table_args__ = (
        Index("idx_stock_master_code", "stock_code"),
        Index("idx_stock_master_active", "is_active"),
        Index("idx_stock_master_market_category_id", "market_category_id"),
        Index("idx_stock_master_sector_33_id", "sector_33_id"),
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
