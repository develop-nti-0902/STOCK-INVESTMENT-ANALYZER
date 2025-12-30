"""株価データ Repository モジュール.

時系列（複数のタイムフレーム）向けの株価データアクセスを提供する基底クラス
と具体的なタイムフレーム別 Repository を実装します。UPSERT と取得ロジックを含みます。

仕様書: docs/architecture/layers/data_access_layer.md 3.2章
"""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional, Union, cast

from sqlalchemy import delete as sql_delete
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

# すべての株価データモデルの型
StockDataModel = Union[
    Stocks1m,
    Stocks5m,
    Stocks15m,
    Stocks30m,
    Stocks1h,
    Stocks1d,
    Stocks1wk,
    Stocks1mo,
]

logger = logging.getLogger(__name__)


class StockDataRepository(BaseRepository, ABC):
    """株価データ向け Repository の基底クラス.

    Attributes:
        timeframe (str): タイムフレーム識別子
            ('1m','5m','15m','30m','1h','1d','1wk','1mo')
        time_column (str): 時間カラム名（'timestamp' または 'date'）
    """

    def __init__(self, session: AsyncSession, model):
        """初期化.

        Args:
            session (AsyncSession): 非同期 DB セッション
            model: 対象となる SQLAlchemy モデルクラス
        """
        super().__init__(session, model)
        self._model = model
        self.timeframe = self._get_timeframe()
        self.time_column = self._get_time_column()

    @property
    def model(self):
        """SQLAlchemyモデルクラス"""
        return self._model

    @abstractmethod
    def _get_timeframe(self) -> str:
        """タイムフレーム識別子を返す（サブクラス実装）.

        Returns:
            str: タイムフレーム識別子
        """

    @abstractmethod
    def _get_time_column(self) -> str:
        """時間カラム名を返す（サブクラス実装）.

        Returns:
            str: 時間カラム名 ('timestamp' または 'date')
        """

    async def upsert_single(self, data: dict) -> dict:
        """単一レコードの UPSERT を実行する.

        Args:
            data (dict): 挿入・更新するデータ（辞書）

        Returns:
            dict: UPSERT 結果情報（operation/rowcount/timeframe/symbol など）

        Raises:
            ValueError: 入力データが不正な場合
            RuntimeError: UPSERT 実行失敗時
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
                "updated_at": func.now(),  # pylint: disable=not-callable
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns, set_=update_values
            )

            # 実行
            result = cast(CursorResult, await self.session.execute(stmt))

            # 結果判定 (ON CONFLICTでは常に1行影響を受ける)
            operation = "upsert" if result.rowcount == 1 else "unknown"

            result_info = {
                "operation": operation,
                "rowcount": result.rowcount,
                "timeframe": self.timeframe,
                "symbol": data["symbol"],
            }

            logger.info(
                "UPSERT executed (no commit): %s %s for %s",
                result_info["operation"],
                self.timeframe,
                data["symbol"],
            )

            return result_info

        except Exception as e:
            # ログにトレースを残す。ロールバックはService層で実行されます。
            logger.exception(
                "UPSERT failed for %s: %s. data=%s",
                self.timeframe,
                e,
                data,
            )
            raise RuntimeError(f"Failed to upsert data: {e}") from e

    async def upsert_bulk(self, data_list: List[dict]) -> int:
        """複数レコードの UPSERT を一括で実行する.

        Args:
            data_list (List[dict]): UPSERT 対象のデータリスト

        Returns:
            int: 成功件数

        Raises:
            RuntimeError: 一括処理に失敗した場合

        Notes:
            トランザクション制御は Service 層で行ってください。
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
                    # 単一レコードのUPSERTで例外が起きた場合はログを記録して次のレコードへ進む
                    error_info = {
                        "data": data,
                        "error": str(e),
                        "timeframe": self.timeframe,
                    }
                    logger.warning("Failed to upsert data: %s", error_info)

            logger.info(
                "Bulk UPSERT executed (no commit): %s/%s succeeded for %s",
                success_count,
                len(data_list),
                self.timeframe,
            )

            return success_count

        except Exception as e:
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
        """銘柄コードと期間で時系列データを取得する.

        Args:
            symbol (str): 銘柄コード
            start (Optional[datetime|date]): 開始時刻/日付（含む）
            end (Optional[datetime|date]): 終了時刻/日付（含む）
            limit (int): 取得上限
            offset (int): オフセット

        Returns:
            List: モデルインスタンスのリスト
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
        """銘柄の最新データを取得する.

        Args:
            symbol (str): 銘柄コード
            limit (int): 取得件数（デフォルト: 1）

        Returns:
            List: 最新のモデルインスタンス（新しい順）
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
        """銘柄ごとのレコード数を返す.

        Args:
            symbol (str): 銘柄コード

        Returns:
            int: レコード数
        """
        # pylint: disable=not-callable
        query = select(func.count()).where(self.model.symbol == symbol)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_symbol_and_timestamp(
        self, symbol: str, timestamp: datetime
    ) -> Optional[StockDataModel]:
        """タイムスタンプベースのデータを取得する（分/時間足用）.

        Args:
            symbol (str): 銘柄コード
            timestamp (datetime): タイムスタンプ

        Returns:
            Optional[StockDataModel]: 見つかればモデルインスタンス、なければ None
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
    ) -> Optional[StockDataModel]:
        """日付ベースのデータを取得する（日足以上用）.

        Args:
            symbol (str): 銘柄コード
            target_date (date): 対象日付

        Returns:
            Optional[StockDataModel]: 見つかればモデルインスタンス、なければ None
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

    async def delete_all(self) -> int:
        """テーブル内の全レコードを削除する.

        Returns:
            int: 削除された件数

        Raises:
            RuntimeError: 削除処理が失敗した場合

        Notes:
            トランザクションのコミット/ロールバックは Service 層で行ってください。
        """
        try:
            stmt = sql_delete(self.model)
            result = cast(CursorResult, await self.session.execute(stmt))

            deleted_count = result.rowcount or 0

            logger.info(
                "Deleted all records from %s: %d rows",
                self.timeframe,
                deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.exception(
                "Failed to delete all records from %s: %s",
                self.timeframe,
                e,
            )
            raise RuntimeError(f"Failed to delete all records: {e}") from e


# 具体的なRepositoryクラス実装


class StockData1mRepository(StockDataRepository):
    """1-minute stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks1m)

    def _get_timeframe(self) -> str:
        return "1m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData5mRepository(StockDataRepository):
    """5-minute stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks5m)

    def _get_timeframe(self) -> str:
        return "5m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData15mRepository(StockDataRepository):
    """15-minute stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks15m)

    def _get_timeframe(self) -> str:
        return "15m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData30mRepository(StockDataRepository):
    """30-minute stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks30m)

    def _get_timeframe(self) -> str:
        return "30m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1hRepository(StockDataRepository):
    """1-hour stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks1h)

    def _get_timeframe(self) -> str:
        return "1h"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1dRepository(StockDataRepository):
    """Daily stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks1d)

    def _get_timeframe(self) -> str:
        return "1d"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1wkRepository(StockDataRepository):
    """Weekly stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks1wk)

    def _get_timeframe(self) -> str:
        return "1wk"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1moRepository(StockDataRepository):
    """Monthly stock data Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Stocks1mo)

    def _get_timeframe(self) -> str:
        return "1mo"

    def _get_time_column(self) -> str:
        return "timestamp"
