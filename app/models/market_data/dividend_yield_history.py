"""配当利回り履歴を保持するデータモデル。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class DividendYieldHistory(
    SerialPKMixin, TimestampMixin, Base
):  # pylint: disable=too-few-public-methods
    """配当利回り履歴を保存するテーブル定義。

    EDINETから取得した年間配当データと株価データから計算された
    日次の配当利回りを履歴として保存。
    """

    # 銘柄コード（FK to STOCK_MASTER.stock_code）
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)

    # 日付
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # 配当金（年間）
    dividend: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 4),
        nullable=True,
        comment="年間配当金（COALESCE(dividend_adj, dividend_actual)）",
    )

    # 株価
    stock_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 4),
        nullable=True,
        comment="株価（COALESCE(adj_close, close)）",
    )

    # 配当利回り
    dividend_yield: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4),
        nullable=True,
        comment="配当利回り = dividend / stock_price",
    )

    # 配当年度
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)

    # 配当取得元ドキュメント
    edinet_document_id: Mapped[int] = mapped_column(
        ForeignKey("edinet_document.id"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_dividend_yield_history_symbol_date"),
        Index("idx_dividend_yield_history_date", "date"),
        Index("idx_dividend_yield_history_symbol_date", "symbol", "date"),
        Index("idx_dividend_yield_history_fiscal_year", "fiscal_year"),
        Index("idx_dividend_yield_history_edinet_document_id", "edinet_document_id"),
    )

    def __repr__(self) -> str:
        """簡易表現を返す（デバッグ用）."""
        return (
            f"<DividendYieldHistory(symbol={self.symbol!r}, "
            f"date={self.date!r}, dividend_yield={self.dividend_yield!r})>"
        )


__all__ = ["DividendYieldHistory"]
