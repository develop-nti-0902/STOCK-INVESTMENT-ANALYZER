"""配当利回り履歴を生成・保存するサービス。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.market_data.dividend_yield_history_repository import (
    DividendYieldHistoryRepository,
)
from app.repositories.market_data.edinet.edinet_stock_dividend_repository import (
    EdinetStockDividendRepository,
)
from app.repositories.market_data.stock_master.stock_code_mapping_repository import (
    StockCodeMappingRepository,
)
from app.repositories.market_data.stock_master.stock_master_repository import StockMasterRepository
from app.repositories.market_data.stock_price.stock_data_repository import StockData1dRepository

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class DividendYieldHistoryResult:  # pylint: disable=too-few-public-methods
    """配当利回り履歴生成結果。

    Attributes:
        rowcount: 生成・UPSERT件数
        skipped_count: スキップ件数（データ不足など）
        error_count: エラー件数
        message: 詳細メッセージ
    """

    rowcount: int
    skipped_count: int
    error_count: int
    message: Optional[str] = None


@dataclass
class DividendYieldHistoryRecord:  # pylint: disable=too-few-public-methods
    """配当利回り履歴レコード。

    Attributes:
        symbol: 銘柄コード
        date: 計算対象日
        dividend: 配当金（年間）
        stock_price: 株価
        dividend_yield: 配当利回り
        fiscal_year: 配当年度
        edinet_document_id: 配当ドキュメントID
    """

    symbol: str
    date: date
    dividend: Optional[Decimal]
    stock_price: Optional[Decimal]
    dividend_yield: Optional[Decimal]
    fiscal_year: int
    edinet_document_id: int

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換（リポジトリ.bulk_upsert用）。"""
        return {
            "symbol": self.symbol,
            "date": self.date,
            "dividend": self.dividend,
            "stock_price": self.stock_price,
            "dividend_yield": self.dividend_yield,
            "fiscal_year": self.fiscal_year,
            "edinet_document_id": self.edinet_document_id,
        }


class DividendYieldHistoryService:  # pylint: disable=too-few-public-methods
    """配当利回り履歴生成サービス。

    複数のリポジトリを組み合わせて、以下の処理を実行：
    1. 全銘柄の取得
    2. 各銘柄について：
        a. stock_code -> sec_code 変換
        b. 指定日付の株価取得
        c. 指定年度の配当取得
        d. 配当利回り計算
        e. DB保存（UPSERT）

    エラーハンドリングは銘柄単位のBest-Effort方式を採用。
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        """初期化。

        Args:
            session_maker: 非同期セッション ファクトリ
        """
        self._session_maker = session_maker

    async def generate_for_date(self, target_date: date) -> DividendYieldHistoryResult:
        """指定日付の配当利回り履歴を生成・保存。

        Args:
            target_date: 計算対象日

        Returns:
            DividendYieldHistoryResult: 生成結果（rowcount、skipped_count、error_count）

        Raises:
            Exception: 予期しないDB例外（銘柄単位のエラーはログして続行）
        """
        logger.info("Starting dividend yield history generation for %s", target_date)

        async with self._session_maker() as session:
            stock_master_repo = StockMasterRepository(session)

            # 有効な全銘柄を取得
            all_symbols = await stock_master_repo.get_all_active_symbols()
            logger.debug("Found %d stocks for processing", len(all_symbols))

            records: List[DividendYieldHistoryRecord] = []
            skipped_count = 0
            error_count = 0

            for symbol in all_symbols:
                try:
                    record = await self._generate_single_stock(session, symbol, target_date)
                    if record:
                        records.append(record)
                    else:
                        skipped_count += 1
                        logger.debug(
                            "Skipped (missing data): symbol=%s, date=%s",
                            symbol,
                            target_date,
                        )
                except Exception:
                    error_count += 1
                    logger.exception(
                        "Error processing symbol=%s, date=%s",
                        symbol,
                        target_date,
                    )
                    # 1銘柄のエラーで全体を中断しない
                    continue

            # Bulk UPSERT
            rowcount = 0
            message = None
            if records:
                repo = DividendYieldHistoryRepository(session)
                record_dicts = [r.to_dict() for r in records]
                rowcount = await repo.bulk_upsert(record_dicts)
                logger.info(
                    "Bulk upserted %d records (skipped=%d, errors=%d)",
                    rowcount,
                    skipped_count,
                    error_count,
                )
                await session.commit()
                message = f"Completed: {rowcount} records upserted"
            else:
                logger.warning(
                    "No records to upsert. skipped=%d, errors=%d",
                    skipped_count,
                    error_count,
                )
                message = f"No records to upsert (skipped={skipped_count}, errors={error_count})"

            return DividendYieldHistoryResult(
                rowcount=rowcount,
                skipped_count=skipped_count,
                error_count=error_count,
                message=message,
            )

    async def _generate_single_stock(
        self, session: AsyncSession, symbol: str, target_date: date
    ) -> Optional[DividendYieldHistoryRecord]:
        """1銘柄の配当利回り履歴レコードを生成。

        Args:
            session: DB セッション
            symbol: 銘柄コード
            target_date: 計算対象日

        Returns:
            生成されたレコード、またはデータ不足時はNone
        """
        # 1. stock_code -> sec_code 変換
        sec_code = await self._resolve_sec_code(session, symbol)
        if not sec_code:
            logger.warning("No SEC code mapping found for symbol=%s", symbol)
            return None

        # 2. 株価取得
        stock_price = await self._get_stock_price(session, symbol, target_date)
        if stock_price is None or stock_price <= 0:
            logger.debug("No valid stock price for symbol=%s on %s", symbol, target_date)
            return None

        # 3. 配当取得（fiscal_year = target_date.year - 1）
        fiscal_year = target_date.year - 1
        dividend_record = await self._get_dividend_record(session, sec_code, fiscal_year)
        if not dividend_record:
            logger.debug("No dividend data for symbol=%s, fiscal_year=%d", symbol, fiscal_year)
            return None

        dividend = await self._get_dividend_amount(dividend_record)
        if dividend is None or dividend <= 0:
            logger.debug("No valid dividend for symbol=%s, fiscal_year=%d", symbol, fiscal_year)
            return None

        # 4. 配当利回り計算
        dividend_yield = self._calculate_dividend_yield(dividend, stock_price)

        # 5. レコード生成
        return DividendYieldHistoryRecord(
            symbol=symbol,
            date=target_date,
            dividend=dividend,
            stock_price=stock_price,
            dividend_yield=dividend_yield,
            fiscal_year=fiscal_year,
            edinet_document_id=dividend_record.edinet_document_id,
        )

    async def _resolve_sec_code(self, session: AsyncSession, symbol: str) -> Optional[str]:
        """stock_code から sec_code を取得。

        Args:
            session: DB セッション
            symbol: 銘柄コード

        Returns:
            SEC コード または None
        """
        repo = StockCodeMappingRepository(session)
        mapping = await repo.get_by_stock_code(symbol)
        return mapping.sec_code if mapping else None

    async def _get_stock_price(
        self, session: AsyncSession, symbol: str, target_date: date
    ) -> Optional[Decimal]:
        """指定日付の株価を取得。

        COALESCE(adj_close, close) の優先順位で選択。

        Args:
            session: DB セッション
            symbol: 銘柄コード
            target_date: 対象日

        Returns:
            株価（Decimal） または None
        """
        repo = StockData1dRepository(session)
        # 対象日のデータを取得（範囲検索で同じ日付）
        # dateオブジェクトをdatetimeに変換してクエリ精度を確保する
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stock_data_list = await repo.get_by_symbol_and_range(
            symbol, start=start_dt, end=end_dt, limit=1
        )
        if not stock_data_list:
            return None

        stock_data = stock_data_list[0]

        # COALESCE(adj_close, close)
        if stock_data.adj_close is not None:
            return Decimal(str(stock_data.adj_close))
        if stock_data.close is not None:
            return Decimal(str(stock_data.close))
        return None

    async def _get_dividend_record(
        self, session: AsyncSession, sec_code: str, fiscal_year: int
    ) -> Optional[Any]:
        """指定年度の配当レコードを取得。

        Args:
            session: DB セッション
            sec_code: SEC コード
            fiscal_year: 会計年度

        Returns:
            配当レコード（EdinetStockDividend） または None
        """
        repo = EdinetStockDividendRepository(session)
        dividends = await repo.find_by_fiscal_year(sec_code, fiscal_year)
        # 複数レコードが返される場合、最新のperiod_end_dateを持つものを返す
        return dividends[0] if dividends else None

    async def _get_dividend_amount(self, dividend_record: Any) -> Optional[Decimal]:
        """配当レコードから配当金を抽出。

        COALESCE(dividend_adj, dividend_actual) の優先順位で選択。

        Args:
            dividend_record: EdinetStockDividend

        Returns:
            配当金（Decimal） または None
        """
        if dividend_record.dividend_adj is not None:
            return Decimal(str(dividend_record.dividend_adj))
        if dividend_record.dividend_actual is not None:
            return Decimal(str(dividend_record.dividend_actual))
        return None

    @staticmethod
    def _calculate_dividend_yield(
        dividend: Optional[Decimal], stock_price: Optional[Decimal]
    ) -> Optional[Decimal]:
        """配当利回りを計算。

        配当利回り = dividend / stock_price
        計算不可時はNone。

        Args:
            dividend: 年間配当
            stock_price: 株価

        Returns:
            配当利回り（Decimal） または None
        """
        if dividend is None or stock_price is None:
            return None
        if dividend <= 0 or stock_price <= 0:
            return None

        try:
            return dividend / stock_price
        except (InvalidOperation, ZeroDivisionError):
            return None


__all__ = [
    "DividendYieldHistoryService",
    "DividendYieldHistoryRecord",
    "DividendYieldHistoryResult",
]
