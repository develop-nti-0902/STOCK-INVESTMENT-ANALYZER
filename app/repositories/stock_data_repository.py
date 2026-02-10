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
from sqlalchemy import desc, select, text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.database import StockDataError
from app.exceptions.validation import FieldValidationError
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
        """SQLAlchemyモデルクラス."""
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
            FieldValidationError: 入力データが不正な場合
            StockDataError: UPSERT 実行失敗時
        """
        if not data:
            raise FieldValidationError(message="Data cannot be empty")

        required_fields = [
            "symbol",
            self.time_column,
            "open",
            "high",
            "low",
            "close",
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise FieldValidationError(message=f"Missing required fields: {missing_fields}")

        try:
            # UPSERT文の構築
            stmt = insert(self.model).values(data)

            # コンフリクト時の更新設定（SQLite互換のUPSERT構文）
            conflict_columns = ["symbol", self.time_column]
            # excluded は on_conflict_do_update 呼び出し後に参照可能になるため、
            # set_ パラメータ内で excluded を使う
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "adj_close": stmt.excluded.adj_close,
                    "volume": stmt.excluded.volume,
                    "updated_at": text("CURRENT_TIMESTAMP"),
                },
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
            raise StockDataError(message=f"Failed to upsert data: {e}") from e

    async def upsert_bulk(self, data_list: List[dict]) -> int:
        """複数レコードの UPSERT を1回のSQL実行でまとめて処理する.

        Args:
            data_list (List[dict]): UPSERT 対象のデータリスト

        Returns:
            int: 成功件数

        Notes:
            - トランザクション制御は Service 層で行ってください。
            - シンボルごとに全データを1回のSQLで処理します。
        """
        if not data_list:
            return 0

        try:
            # 事前に必須フィールドの検証を行い、無効なレコードは除外する
            valid_data: List[dict] = []
            for data in data_list:
                required_fields = [
                    "symbol",
                    self.time_column,
                    "open",
                    "high",
                    "low",
                    "close",
                ]
                missing_fields: List[str] = []
                for field in required_fields:
                    if field not in data:
                        missing_fields.append(field)
                if missing_fields:
                    logger.warning(
                        "Skipping invalid upsert (missing=%s): %s",
                        missing_fields,
                        data,
                    )
                    continue
                valid_data.append(data)

            if not valid_data:
                logger.info("No valid data to upsert for %s", self.timeframe)
                return 0

            # PostgreSQLのパラメータ制限(32767)を考慮
            # 安全マージンとして3000レコード(24000パラメータ)を上限とする
            max_records_per_query = 3000
            total_params = len(valid_data) * 8

            if total_params > 24000:  # 3000レコード × 8カラム
                logger.info(
                    "Large dataset for %s: %s records (%s parameters). Splitting into chunks.",
                    self.timeframe,
                    len(valid_data),
                    total_params,
                )

                # チャンクに分割して処理
                success_count = 0
                for i in range(0, len(valid_data), max_records_per_query):
                    chunk = valid_data[i : i + max_records_per_query]

                    chunk_count = await self._execute_insert(chunk)
                    success_count += chunk_count

                    logger.debug(
                        "Chunk %s-%s: %s rows affected",
                        i,
                        i + len(chunk),
                        chunk_count,
                    )
            else:
                logger.info(
                    "Starting bulk upsert for %s: %s valid records (out of %s total)",
                    self.timeframe,
                    len(valid_data),
                    len(data_list),
                )

                # 全データを1回のSQLで実行
                success_count = await self._execute_insert(valid_data)

            msg = (
                "Bulk UPSERT executed (no commit): "
                f"{success_count}/{len(data_list)} rows affected "
                f"for {self.timeframe} (valid_data={len(valid_data)})"
            )
            logger.info(msg)

            return success_count

        except Exception as e:
            logger.error("Bulk UPSERT failed for %s: %s", self.timeframe, e)
            raise StockDataError(message=f"Failed to bulk upsert data: {e}") from e

    async def _execute_insert(self, chunk: List[dict]) -> int:
        """チャンク用のUPSERT文を構築して実行するヘルパー."""
        stmt = insert(self.model).values(chunk)
        # excluded は on_conflict_do_update 呼び出し後に参照可能になる
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", self.time_column],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
                "updated_at": text("CURRENT_TIMESTAMP"),
            },
        )

        result = await self.session.execute(stmt)
        return result.rowcount if hasattr(result, "rowcount") and result.rowcount else len(chunk)

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
        query = select(text(f"count({self.model.symbol.name})")).where(self.model.symbol == symbol)
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
            raise FieldValidationError(
                message=f"This method is for timestamp-based data. "
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
            raise FieldValidationError(
                message=f"This method is for date-based data. "
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
            raise StockDataError(message=f"Failed to delete all records: {e}") from e


# 具体的なRepositoryクラス実装


class StockData1mRepository(StockDataRepository):
    """1-minute stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks1m` モデルをセットします."""
        super().__init__(session, Stocks1m)

    def _get_timeframe(self) -> str:
        return "1m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData5mRepository(StockDataRepository):
    """5-minute stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks5m` モデルをセットします."""
        super().__init__(session, Stocks5m)

    def _get_timeframe(self) -> str:
        return "5m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData15mRepository(StockDataRepository):
    """15-minute stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks15m` モデルをセットします."""
        super().__init__(session, Stocks15m)

    def _get_timeframe(self) -> str:
        return "15m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData30mRepository(StockDataRepository):
    """30-minute stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks30m` モデルをセットします."""
        super().__init__(session, Stocks30m)

    def _get_timeframe(self) -> str:
        return "30m"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1hRepository(StockDataRepository):
    """1-hour stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks1h` モデルをセットします."""
        super().__init__(session, Stocks1h)

    def _get_timeframe(self) -> str:
        return "1h"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1dRepository(StockDataRepository):
    """Daily stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks1d` モデルをセットします."""
        super().__init__(session, Stocks1d)

    def _get_timeframe(self) -> str:
        return "1d"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1wkRepository(StockDataRepository):
    """Weekly stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks1wk` モデルをセットします."""
        super().__init__(session, Stocks1wk)

    def _get_timeframe(self) -> str:
        return "1wk"

    def _get_time_column(self) -> str:
        return "timestamp"


class StockData1moRepository(StockDataRepository):
    """Monthly stock data Repository."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Stocks1mo` モデルをセットします."""
        super().__init__(session, Stocks1mo)

    def _get_timeframe(self) -> str:
        return "1mo"

    def _get_time_column(self) -> str:
        return "timestamp"
