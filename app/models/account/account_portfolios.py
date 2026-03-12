"""アカウント保有ポートフォリオ（account_portfolios）テーブルのモデル定義モジュール.

`docs/architecture/layers/data_storage_layer.md` の定義に合わせたポートフォリオ保存用モデル.
プロジェクト内の他モデルと同様に `SerialPKMixin` と `TimestampMixin` を利用します.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class AccountPortfolios(SerialPKMixin, TimestampMixin, Base):
    """アカウントが保有するポートフォリオの銘柄毎エントリを表すモデル.

    Attributes:
        account_id: `accounts.id` への外部キー
        portfolio_name: ポートフォリオ名（複数ポートフォリオを想定）
        symbol: 銘柄コード
        quantity: 保有株数
        avg_price: 取得平均単価
        market_value: 時価（任意に更新）
        currency: 通貨コード
        valuation_date: 時価計算日
        allocation: ポートフォリオ内比率（割合、小数）
        note: 任意のメモ
    """

    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("account.id"),
        nullable=False,
    )
    portfolio_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    market_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    valuation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    allocation: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_account_portfolios_account", "account_id"),
        Index("idx_account_portfolios_symbol", "symbol"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用)."""
        return (
            "<AccountPortfolios(account_id="
            f"{self.account_id!r}, symbol={self.symbol!r}, "
            f"quantity={self.quantity!r})>"
        )


__all__ = ["AccountPortfolios"]
