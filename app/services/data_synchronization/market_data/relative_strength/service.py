"""レラティブストレングス計算・保存サービス."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.market_data.stock_price import Stocks1d
from app.repositories.market_data.relative_strength import RelativeStrengthRepository
from app.repositories.market_data.stock_master.stock_master_repository import StockMasterRepository

logger = logging.getLogger(__name__)

# 計算に使う重み
WEIGHT_63 = Decimal("0.4")
WEIGHT_126 = Decimal("0.2")
WEIGHT_189 = Decimal("0.2")
WEIGHT_252 = Decimal("0.2")


@dataclass
class RelativeStrengthResult:
    """指定日付の計算結果."""

    rowcount: int
    skipped_count: int
    error_count: int
    calculation_date: date
    message: Optional[str] = None


@dataclass
class RelativeStrengthAllResult:
    """全期間計算結果."""

    total_symbols: int
    total_rowcount: int
    error_count: int
    message: Optional[str] = None


class RelativeStrengthService:
    """レラティブストレングス計算サービス."""

    PERIODS = (63, 126, 189, 252)
    WEIGHTS = (WEIGHT_63, WEIGHT_126, WEIGHT_189, WEIGHT_252)

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        """セッションメーカーを受け取り、RSサービスを初期化します."""
        self._session_maker = session_maker

    async def calculate_for_date(self, calculation_date: date) -> RelativeStrengthResult:
        """指定日付の全銘柄のRSを計算・UPSERT."""
        logger.info("Starting RS calculation for %s", calculation_date)

        async with self._session_maker() as session:
            stock_master_repo = StockMasterRepository(session)
            all_symbols = await stock_master_repo.get_all_active_symbols()

            records: List[dict[str, Any]] = []
            skipped_count = 0
            error_count = 0

            for symbol in all_symbols:
                try:
                    record = await self._calculate_single_for_date(
                        session, symbol, calculation_date
                    )
                    if record:
                        records.append(record)
                    else:
                        skipped_count += 1
                except Exception:
                    error_count += 1
                    logger.exception("Error processing symbol=%s date=%s", symbol, calculation_date)

            rowcount = 0
            if records:
                repo = RelativeStrengthRepository(session)
                rowcount = await repo.bulk_upsert(records)
                await session.commit()

            message = (
                f"Completed: {rowcount} upserted, " f"{skipped_count} skipped, {error_count} errors"
            )
            return RelativeStrengthResult(
                rowcount=rowcount,
                skipped_count=skipped_count,
                error_count=error_count,
                calculation_date=calculation_date,
                message=message,
            )

    async def _calculate_single_for_date(
        self, session: AsyncSession, symbol: str, calculation_date: date
    ) -> Optional[dict[str, Any]]:
        """1銘柄・1日付のRSレコードを計算."""
        upper_ts = datetime(
            calculation_date.year,
            calculation_date.month,
            calculation_date.day,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        )

        stmt = (
            select(Stocks1d)
            .where(Stocks1d.symbol == symbol)
            .where(Stocks1d.timestamp <= upper_ts)
            .order_by(Stocks1d.timestamp.asc())
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        if not rows:
            return None

        last_row = rows[-1]
        last_date = (
            last_row.timestamp.date() if hasattr(last_row.timestamp, "date") else last_row.timestamp
        )
        if last_date != calculation_date:
            return None

        closes: List[Optional[Decimal]] = []
        for row in rows:
            close = row.adj_close if row.adj_close is not None else row.close
            closes.append(close)

        n = len(closes)
        current_close = closes[-1]

        if not current_close or current_close == 0:
            return None

        def get_change(offset: int) -> Optional[Decimal]:
            idx = n - 1 - offset
            if idx < 0:
                return None
            past_close = closes[idx]
            if not past_close or past_close == 0:
                return None
            try:
                ratio = (current_close / past_close) - Decimal("1")  # type: ignore[operator]
                return ratio * Decimal("100")
            except (InvalidOperation, ZeroDivisionError):
                return None

        c63 = get_change(63)
        c126 = get_change(126)
        c189 = get_change(189)
        c252 = get_change(252)

        if all(v is not None for v in [c63, c126, c189, c252]):
            score = (
                WEIGHT_63 * c63  # type: ignore[operator]
                + WEIGHT_126 * c126  # type: ignore[operator]
                + WEIGHT_189 * c189  # type: ignore[operator]
                + WEIGHT_252 * c252  # type: ignore[operator]
            )
        else:
            score = None

        return {
            "symbol": symbol,
            "calculation_date": calculation_date,
            "change_63days": c63,
            "change_126days": c126,
            "change_189days": c189,
            "change_252days": c252,
            "relative_strength_score": score,
        }

    async def calculate_all(self) -> RelativeStrengthAllResult:
        """全銘柄・全期間のRSを計算・UPSERT（per-symbol戦略）."""
        logger.info("Starting RS calculation for all periods (per-symbol strategy)")

        async with self._session_maker() as session:
            stock_master_repo = StockMasterRepository(session)
            all_symbols = await stock_master_repo.get_all_active_symbols()

            total_rowcount = 0
            error_count = 0

            for symbol in all_symbols:
                try:
                    result_data = await self._calculate_all_for_symbol(session, symbol)
                    if result_data:
                        repo = RelativeStrengthRepository(session)
                        rc = await repo.bulk_upsert(result_data)
                        total_rowcount += rc
                        await session.commit()
                except Exception:
                    error_count += 1
                    logger.exception("Error processing all dates for symbol=%s", symbol)

            total_symbols = len(all_symbols)
            message = (
                f"Completed: {total_rowcount} upserted, "
                f"{total_symbols} symbols, {error_count} errors"
            )
            return RelativeStrengthAllResult(
                total_symbols=total_symbols,
                total_rowcount=total_rowcount,
                error_count=error_count,
                message=message,
            )

    async def _calculate_all_for_symbol(
        self, session: AsyncSession, symbol: str
    ) -> List[dict[str, Any]]:
        """1銘柄の全日付分RSレコードを生成（スライドウィンドウ）."""
        stmt = select(Stocks1d).where(Stocks1d.symbol == symbol).order_by(Stocks1d.timestamp.asc())
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        if not rows:
            return []

        closes: List[Optional[Decimal]] = []
        dates: List[date] = []
        for row in rows:
            close = row.adj_close if row.adj_close is not None else row.close
            closes.append(close)
            ts = row.timestamp
            d = ts.date() if hasattr(ts, "date") else ts
            dates.append(d)

        records = []
        n = len(closes)
        for i in range(n):
            current_close = closes[i]
            if not current_close or current_close == 0:
                continue

            def get_change_at(idx_current: int, offset: int) -> Optional[Decimal]:
                idx = idx_current - offset
                if idx < 0:
                    return None
                past_close = closes[idx]
                if not past_close or past_close == 0:
                    return None
                try:
                    ratio = (closes[idx_current] / past_close) - Decimal("1")  # type: ignore
                    return ratio * Decimal("100")
                except (InvalidOperation, ZeroDivisionError):
                    return None

            c63 = get_change_at(i, 63)
            c126 = get_change_at(i, 126)
            c189 = get_change_at(i, 189)
            c252 = get_change_at(i, 252)

            if all(v is not None for v in [c63, c126, c189, c252]):
                score = (
                    WEIGHT_63 * c63  # type: ignore[operator]
                    + WEIGHT_126 * c126  # type: ignore[operator]
                    + WEIGHT_189 * c189  # type: ignore[operator]
                    + WEIGHT_252 * c252  # type: ignore[operator]
                )
            else:
                score = None

            records.append(
                {
                    "symbol": symbol,
                    "calculation_date": dates[i],
                    "change_63days": c63,
                    "change_126days": c126,
                    "change_189days": c189,
                    "change_252days": c252,
                    "relative_strength_score": score,
                }
            )

        return records
