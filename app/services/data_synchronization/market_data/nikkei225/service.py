"""日経225データ取得・保存オーケストレーション層."""

from __future__ import annotations

from time import perf_counter
from typing import Optional

from app.services.data_synchronization.market_data.nikkei225.converter import Nikkei225Converter
from app.services.data_synchronization.market_data.nikkei225.fetcher import Nikkei225Fetcher
from app.services.data_synchronization.market_data.nikkei225.saver import Nikkei225Saver
from app.services.data_synchronization.market_data.nikkei225.validator import Nikkei225Validator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei225ServiceResult:
    """サービス実行結果.

    Attributes:
        success: 全体の成功/失敗
        records_fetched: 取得したレコード数
        records_saved: 保存したレコード数
        errors: エラーメッセージリスト
        warnings: 警告メッセージリスト
        elapsed_time: 処理時間（秒）
    """

    def __init__(
        self,
        success: bool,
        records_fetched: int = 0,
        records_saved: int = 0,
        errors: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        elapsed_time: float = 0.0,
    ) -> None:
        """結果オブジェクトを初期化する."""
        self.success = success
        self.records_fetched = records_fetched
        self.records_saved = records_saved
        self.errors: list[str] = errors or []
        self.warnings: list[str] = warnings or []
        self.elapsed_time = elapsed_time

    def __repr__(self) -> str:
        """デバッグ用文字列表現."""
        return (
            f"Nikkei225ServiceResult("
            f"success={self.success}, "
            f"records_fetched={self.records_fetched}, "
            f"records_saved={self.records_saved}, "
            f"elapsed_time={self.elapsed_time:.2f}s)"
        )


class Nikkei225Service:
    """日経225データ取得・保存オーケストレーション層.

    Fetcher → Converter → Validator → Saver の順で処理を行う。
    """

    def __init__(
        self,
        fetcher: Nikkei225Fetcher,
        converter: Nikkei225Converter,
        validator: Nikkei225Validator,
        saver: Nikkei225Saver,
    ) -> None:
        """初期化.

        Args:
            fetcher: データ取得クラス
            converter: データ変換クラス
            validator: データ検証クラス
            saver: データ保存クラス
        """
        self.fetcher = fetcher
        self.converter = converter
        self.validator = validator
        self.saver = saver

    async def fetch_and_save(self, max_period: Optional[int] = None) -> Nikkei225ServiceResult:
        """全フローを実行する.

        1. Fetcher.fetch(max_period) → DataFrame
        2. Converter.from_dataframe(df) → list[Nikkei2251dCreate]
        3. Validator.validate(data) → ValidationResult
        4. Converter.to_saver_records(models) → list[dict]
        5. Saver.save(records) → int

        Args:
            max_period: 取得日数上限（None = 全データ）

        Returns:
            Nikkei225ServiceResult
        """
        start = perf_counter()
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # 1. データ取得
            df = await self.fetcher.fetch(max_period=max_period)
            if df.empty:
                return Nikkei225ServiceResult(
                    success=True,
                    records_fetched=0,
                    records_saved=0,
                    warnings=["No data returned from yfinance"],
                    elapsed_time=perf_counter() - start,
                )

            # 2. DataFrame → Pydantic スキーマ変換
            models = self.converter.from_dataframe(df)
            records_fetched = len(models)

            # 3. バリデーション
            validation_result = self.validator.validate(models)
            warnings.extend(validation_result.warnings)
            if not validation_result.is_valid:
                errors.extend(validation_result.errors)
                return Nikkei225ServiceResult(
                    success=False,
                    records_fetched=records_fetched,
                    records_saved=0,
                    errors=errors,
                    warnings=warnings,
                    elapsed_time=perf_counter() - start,
                )

            # 4. Saver 用辞書変換
            records = self.converter.to_saver_records(models)

            # 5. DB 保存
            records_saved = await self.saver.save(records)

            elapsed = perf_counter() - start
            logger.info(
                "Nikkei225Service completed: fetched=%d, saved=%d, elapsed=%.2fs",
                records_fetched,
                records_saved,
                elapsed,
            )
            return Nikkei225ServiceResult(
                success=True,
                records_fetched=records_fetched,
                records_saved=records_saved,
                errors=errors,
                warnings=warnings,
                elapsed_time=elapsed,
            )

        except Exception as exc:
            error_msg = f"Nikkei225Service failed: {exc}"
            logger.exception(error_msg)
            errors.append(error_msg)
            return Nikkei225ServiceResult(
                success=False,
                records_fetched=0,
                records_saved=0,
                errors=errors,
                warnings=warnings,
                elapsed_time=perf_counter() - start,
            )
