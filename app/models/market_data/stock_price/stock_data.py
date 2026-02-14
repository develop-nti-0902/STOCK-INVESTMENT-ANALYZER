"""株価データモデル群. 各時間軸の株価データテーブル定義を提供します."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class _CommonPriceColumns:
    """共通の価格カラム定義をまとめたヘルパークラス（継承用）.

    Attributes:
        open (Decimal): 始値
        high (Decimal): 高値
        low (Decimal): 安値
        close (Decimal): 終値
        adj_close (Optional[Decimal]): 調整終値 (yfinance の `Adj Close`)
        volume (int): 出来高
    """

    open: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    # 調整終値 (yfinance の `Adj Close`) を格納するためのカラム
    adj_close: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    def price_fields(self) -> list[str]:  # pragma: no cover - trivial
        """価格系のカラム名リストを返すヘルパー（テスト/デバッグ用)."""
        return ["open", "high", "low", "close", "adj_close", "volume"]

    def has_adj_close(self) -> bool:  # pragma: no cover - trivial
        """このモデルが調整終値(`adj_close`)カラムを持つかを示すフラグ（常にTrue)."""
        return True


class Stocks1m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """1分足の株価データモデル.

    Attributes:
        symbol (str): 銘柄コード（`stock_master.stock_code` 参照）
        timestamp (datetime): タイムスタンプ（JST）
        open/high/low/close/adj_close/volume: 価格系の共通カラム
    """

    __tablename__ = "stocks_1m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_1m_symbol_timestamp"),
        Index("idx_stocks_1m_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks5m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """5分足の株価データモデル.

    Attributes:
        symbol (str): 銘柄コード
        timestamp (datetime): タイムスタンプ（JST）
    """

    __tablename__ = "stocks_5m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_5m_symbol_timestamp"),
        Index("idx_stocks_5m_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks15m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """15分足の株価データモデル."""

    __tablename__ = "stocks_15m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_15m_symbol_timestamp"),
        Index("idx_stocks_15m_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks30m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """30分足の株価データモデル."""

    __tablename__ = "stocks_30m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stock_master.stock_code",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_30m_symbol_timestamp"),
        Index("idx_stocks_30m_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks1h(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """1時間足の株価データモデル."""

    __tablename__ = "stocks_1h"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_1h_symbol_timestamp"),
        Index("idx_stocks_1h_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks1d(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """日足の株価データモデル."""

    __tablename__ = "stocks_1d"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_1d_symbol_timestamp"),
        Index("idx_stocks_1d_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks1wk(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """週足の株価データモデル."""

    __tablename__ = "stocks_1wk"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_1wk_symbol_timestamp"),
        Index("idx_stocks_1wk_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


class Stocks1mo(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    """月足の株価データモデル."""

    __tablename__ = "stocks_1mo"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uix_stocks_1mo_symbol_timestamp"),
        Index("idx_stocks_1mo_timestamp", "timestamp"),
    )

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返す（ログやテストで利用）。"""
        return self.__class__.__name__


# Exported names are managed in `app/models/__init__.py`
