from __future__ import annotations

"""銘柄マスタモデル定義モジュール.

管理用の `stock_master` テーブルに合わせたモデルを定義します。
既存スキーマとの互換性を保つためのインデックスやカラム制約を含みます。
"""

from typing import Optional

from sqlalchemy import Index, Integer, String

# pylint: disable=too-few-public-methods
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin

# is_active カラムの値を表す定数
# 0/1 の整数をそのまま使うのではなく、名前付き定数を用いることで可読性と保守性を高める
IS_ACTIVE = 1
IS_INACTIVE = 0


class StockMaster(SerialPKMixin, TimestampMixin, Base):
    """管理DBの `stock_master` テーブルに合わせたモデル定義.

    Attributes:
        stock_code (str): ユニークな銘柄コード
        stock_name (str): 銘柄名
        market_category (Optional[str]): 市場カテゴリ
        sector_code_33 (Optional[str]): 33業種コード
        sector_name_33 (Optional[str]): 33業種名
        sector_code_17 (Optional[str]): 17業種コード
        sector_name_17 (Optional[str]): 17業種名
        scale_code (Optional[str]): 規模コード
        scale_category (Optional[str]): 規模カテゴリ
        data_date (Optional[str]): データ日付（YYYYMMDD）
        is_active (int): 有効フラグ（`IS_ACTIVE` / `IS_INACTIVE`）

        Notes:
                - `scripts/databaseSetup/sql/create_management_tables.sql`
                    に合わせたカラム定義です。
                - 後方互換性のため `symbol` / `name` のプロパティを提供します。
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
        """`stock_code` の互換プロパティ（読み取り）.

        Returns:
            str: `stock_code` と同じ値
        """
        return self.stock_code

    @symbol.setter
    def symbol(self, value: str) -> None:
        """`stock_code` の互換プロパティ（書き込み）.

        Args:
            value (str): 新しい銘柄コード
        """
        self.stock_code = value

    @property
    def name(self) -> str:
        """`stock_name` の互換プロパティ（読み取り）.

        Returns:
            str: `stock_name` と同じ値
        """
        return self.stock_name

    @name.setter
    def name(self, value: str) -> None:
        """`stock_name` の互換プロパティ（書き込み）.

        Args:
            value (str): 新しい銘柄名
        """
        self.stock_name = value

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockMaster(stock_code="
            f"{self.stock_code!r}, stock_name={self.stock_name!r})>"
        )


__all__ = ["StockMaster"]
