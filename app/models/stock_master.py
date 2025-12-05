from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockMaster(SerialPKMixin, TimestampMixin, Base):
    """管理DBの `stock_master` テーブルに合わせたモデル定義。

    DB スクリプト `scripts/databaseSetup/sql/create_management_tables.sql` に合わせて
    カラム名・型・インデックスを定義しています。
    - `stock_code` はユニークな銘柄コード
    - 既存の実運用スキーマと互換性を保つため `id` を主キーにしています
    """

    stock_code: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=True
    )
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    market_category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    sector_code_33: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    sector_name_33: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    sector_code_17: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    sector_name_17: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    scale_code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    scale_category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    data_date: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("idx_stock_master_code", "stock_code"),
        Index("idx_stock_master_active", "is_active"),
        Index("idx_stock_master_market", "market_category"),
        Index("idx_stock_master_sector_33", "sector_code_33"),
    )

    # 互換性ヘルパー: 以前の `symbol` / `name` を使っている箇所向けにプロパティを提供
    @property
    def symbol(self) -> str:
        return self.stock_code

    @symbol.setter
    def symbol(self, value: str) -> None:
        self.stock_code = value

    @property
    def name(self) -> str:
        return self.stock_name

    @name.setter
    def name(self, value: str) -> None:
        self.stock_name = value

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockMaster(stock_code="
            f"{self.stock_code!r}, stock_name={self.stock_name!r})>"
        )


__all__ = ["StockMaster"]
