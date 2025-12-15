"""
株価データRepository

StockDataRepositoryの基底クラスと8種類のタイムフレーム別Repositoryを実装します。
UPSERT処理と時系列データ取得を提供します。

仕様書: docs/architecture/layers/data_access_layer.md 3.2章
"""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional, Union, cast

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_data import (
    Stocks1d,
    Stocks1h,
    Stocks1m,
    Stocks1mo,
    Stocks1wk,
    Stocks5m,
    Stocks15m,
    Stocks30m,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class StockDataRepository(BaseRepository, ABC):
    """
    株価データRepository基底クラス

    8種類のタイムフレーム別Repositoryの基底クラスとして、
    UPSERT処理と時系列データ取得を提供します。

    Attributes:
        timeframe (str): タイムフレーム識別子
            ('1m', '5m', '15m', '30m', '1h', '1d', '1wk', '1mo')
        time_column (str): 時間カラム名（'timestamp' または 'date'）
    """

    def __init__(self, session: AsyncSession):
        """
        初期化

        Args:
            session: 非同期DBセッション
        """
        super().__init__(session, self.model)
        self.timeframe = self._get_timeframe()
        self.time_column = self._get_time_column()

    @property
    @abstractmethod
    def model(self):
        """SQLAlchemyモデルクラス（サブクラスで実装）"""

    @abstractmethod
    def _get_timeframe(self) -> str:
        """タイムフレーム識別子を取得（サブクラスで実装）"""

    @abstractmethod
    def _get_time_column(self) -> str:
        """時間カラム名を取得（サブクラスで実装）"""

    async def upsert_single(self, data: dict) -> dict:
        """
        単一レコードのUPSERT

        Args:
            data: 挿入・更新するデータ（辞書形式）

        Returns:
            dict: UPSERT結果情報

        Raises:
            ValueError: データが不正な場合
            RuntimeError: UPSERT処理に失敗した場合
        """
        if not data:
            raise ValueError("Data cannot be empty")

        required_fields = [
            "symbol",
            self.time_column,
            "open",
            "high",
            "low",
            "close",
        ]
        missing_fields = [
            field for field in required_fields if field not in data
        ]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        try:
            # UPSERT文の構築
            stmt = insert(self.model).values(data)

            # コンフリクト時の更新設定
            conflict_columns = ["symbol", self.time_column]
            update_values = {
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
                "updated_at": func.now(),
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns, set_=update_values
            )

            # 実行
            result = cast(CursorResult, await self.session.execute(stmt))
            await self.session.commit()

            # 結果判定 (ON CONFLICTでは常に1行影響を受ける)
            operation = "upsert" if result.rowcount == 1 else "unknown"

            result_info = {
                "operation": operation,
                "rowcount": result.rowcount,
                "timeframe": self.timeframe,
                "symbol": data["symbol"],
            }

            logger.info(
                "UPSERT completed: %s %s for %s",
                result_info["operation"],
                self.timeframe,
                data["symbol"],
            )

            return result_info

        except Exception as e:
            await self.session.rollback()
            logger.error("UPSERT failed for %s: %s", self.timeframe, e)
            raise RuntimeError(f"Failed to upsert data: {e}") from e

    async def upsert_bulk(self, data_list: List[dict]) -> int:
        """
        一括UPSERT

        Args:
            data_list: UPSERTするデータのリスト

        Returns:
            int: 成功した件数

        Raises:
            ValueError: データリストが不正な場合
            RuntimeError: UPSERT処理に失敗した場合
        """
        if not data_list:
            return 0

        success_count = 0

        try:
            # 全データをUPSERT
            for data in data_list:
                try:
                    await self.upsert_single(data)
                    success_count += 1
                except Exception as e:
                    error_info = {
                        "data": data,
                        "error": str(e),
                        "timeframe": self.timeframe,
                    }
                    logger.warning("Failed to upsert data: %s", error_info)

            logger.info(
                "Bulk UPSERT completed: %s/%s succeeded for %s",
                success_count,
                len(data_list),
                self.timeframe,
            )

            return success_count

        except Exception as e:
            await self.session.rollback()
            logger.error("Bulk UPSERT failed for %s: %s", self.timeframe, e)
            raise RuntimeError(f"Failed to bulk upsert data: {e}") from e

    async def get_by_symbol_and_range(
        self,
        symbol: str,
        start: Optional[Union[datetime, date]] = None,
        end: Optional[Union[datetime, date]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List:
        """
        銘柄コードと期間指定でデータを取得

        Args:
            symbol: 銘柄コード
            start: 開始日時/日付（含む）
            end: 終了日時/日付（含む）
            limit: 取得件数上限
            offset: オフセット

        Returns:
            モデルインスタンスのリスト
        """
        query = select(self.model).where(self.model.symbol == symbol)

        time_col = getattr(self.model, self.time_column)

        if start is not None:
            query = query.where(time_col >= start)
        if end is not None:
            query = query.where(time_col <= end)

        query = query.order_by(desc(time_col)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, symbol: str, limit: int = 1) -> List:
        """
        銘柄の最新データを取得

        Args:
            symbol: 銘柄コード
            limit: 取得件数

        Returns:
            最新のモデルインスタンスリスト（新しい順）
        """
        time_col = getattr(self.model, self.time_column)

        query = (
            select(self.model)
            .where(self.model.symbol == symbol)
            .order_by(desc(time_col))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_symbol(self, symbol: str) -> int:
        """
        銘柄のレコード数を取得

        Args:
            symbol: 銘柄コード

        Returns:
            レコード数
        """
        query = select(func.count()).where(self.model.symbol == symbol)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_symbol_and_timestamp(
        self, symbol: str, timestamp: datetime
    ) -> Optional:
        """
        銘柄コード + タイムスタンプでデータを取得（分足・時間足用）

        Args:
            symbol: 銘柄コード
            timestamp: タイムスタンプ

        Returns:
            モデルインスタンス、見つからない場合はNone
        """
        if self.time_column != "timestamp":
            raise ValueError(
                f"This method is for timestamp-based data. "
                f"Use get_by_symbol_and_date for {self.timeframe}"
            )

        query = select(self.model).where(
            self.model.symbol == symbol,
            self.model.timestamp == timestamp,
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_symbol_and_date(
        self, symbol: str, target_date: date
    ) -> Optional:
        """
        銘柄コード + 日付でデータを取得（日足以上用）

        Args:
            symbol: 銘柄コード
            target_date: 対象日付

        Returns:
            モデルインスタンス、見つからない場合はNone
        """
        if self.time_column != "date":
            raise ValueError(
                f"This method is for date-based data. "
                f"Use get_by_symbol_and_timestamp for {self.timeframe}"
            )

        query = select(self.model).where(
            self.model.symbol == symbol,
            self.model.date == target_date,
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()


# 具体的なRepositoryクラス実装


class StockData1mRepository(StockDataRepository):
    """1-minute stock data Repository"""

    model = Stocks1m

    def _get_timeframe(self) -> str:
        return "1m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData5mRepository(StockDataRepository):
    """5-minute stock data Repository"""

    model = Stocks5m

    def _get_timeframe(self) -> str:
        return "5m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData15mRepository(StockDataRepository):
    """15-minute stock data Repository"""

    model = Stocks15m

    def _get_timeframe(self) -> str:
        return "15m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData30mRepository(StockDataRepository):
    """30-minute stock data Repository"""

    model = Stocks30m

    def _get_timeframe(self) -> str:
        return "30m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1hRepository(StockDataRepository):
    """1-hour stock data Repository"""

    model = Stocks1h

    def _get_timeframe(self) -> str:
        return "1h"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1dRepository(StockDataRepository):
    """Daily stock data Repository"""

    model = Stocks1d

    def _get_timeframe(self) -> str:
        return "1d"

    def _get_time_column(self) -> str:
        return "date"


class StockData1wkRepository(StockDataRepository):
    """Weekly stock data Repository"""

    model = Stocks1wk

    def _get_timeframe(self) -> str:
        return "1wk"

    def _get_time_column(self) -> str:
        return "date"


class StockData1moRepository(StockDataRepository):
    """Monthly stock data Repository"""

    model = Stocks1mo

    def _get_timeframe(self) -> str:
        return "1mo"

    def _get_time_column(self) -> str:
        return "date"
