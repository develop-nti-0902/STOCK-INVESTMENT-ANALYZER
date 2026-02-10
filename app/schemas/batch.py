"""バッチ API 用の Pydantic スキーマ定義.

バッチジョブの作成／進捗管理／履歴取得に用いるリクエスト／レスポンススキーマと
バッチ実行に関するモデル（JobType, JobStatus, BatchExecution*）を提供します。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseRequestSchema, BaseResponseSchema, PaginationResponseSchema


class SingleStockDataRequest(BaseRequestSchema):
    """単一銘柄のデータ取得リクエスト.

    Attributes:
        symbol (str): 銘柄コード
        timeframe (str): タイムフレーム
        start_date (str): 開始日
        end_date (str): 終了日
    """

    symbol: str = Field(..., description="銘柄コード")
    timeframe: str = Field(..., description="タイムフレーム")
    start_date: str = Field(..., description="開始日")
    end_date: str = Field(..., description="終了日")


class JPXAllStocksRequest(BaseRequestSchema):
    """JPX 全銘柄取得リクエスト.

    Attributes:
        timeframe (str): タイムフレーム
        start_date (str): 開始日
        end_date (str): 終了日
        market (Optional[str]): 市場区分
    """

    timeframe: str = Field(..., description="タイムフレーム")
    start_date: str = Field(..., description="開始日")
    end_date: str = Field(..., description="終了日")
    market: Optional[str] = Field(None, description="市場区分")


class BatchJobResponse(BaseResponseSchema):
    """ジョブ作成レスポンス.

    Attributes:
        job_id (str): ジョブID
        job_type (str): ジョブ種別
        status (str): ジョブステータス
        estimated_completion (Optional[str]): 推定完了日時（ISO-8601）
    """

    job_id: str = Field(..., description="ジョブID")
    job_type: str = Field(..., description="ジョブ種別")
    status: str = Field(..., description="ジョブステータス")
    estimated_completion: Optional[str] = Field(None, description="推定完了日時（ISO-8601）")


class BatchJobProgress(BaseRequestSchema):
    """ジョブ進捗情報スキーマ.

    Attributes:
        processed (int): 処理済み件数
        total (int): 総件数
        percentage (float): 進捗率（0-100）
    """

    processed: int = Field(..., description="処理済み件数", ge=0)
    total: int = Field(..., description="総件数", ge=0)
    percentage: float = Field(..., description="進捗率（0-100）")


class BatchJobStatusResponse(BaseResponseSchema):
    """ジョブステータスレスポンス（進捗情報含む）.

    Attributes:
        job_id (str): ジョブID
        job_type (str): ジョブ種別
        status (str): ジョブステータス
        progress (BatchJobProgress): 進捗情報
        started_at (str): 開始日時（ISO-8601）
        estimated_completion (Optional[str]): 推定完了日時（ISO-8601）
    """

    job_id: str = Field(..., description="ジョブID")
    job_type: str = Field(..., description="ジョブ種別")
    status: str = Field(..., description="ジョブステータス")
    progress: BatchJobProgress = Field(..., description="進捗情報")
    started_at: str = Field(..., description="開始日時（ISO-8601）")
    estimated_completion: Optional[str] = Field(None, description="推定完了日時（ISO-8601）")


class BatchHistoryItem(BaseRequestSchema):
    """バッチ履歴アイテムスキーマ.

    Attributes:
        job_id (str): ジョブID
        job_type (str): ジョブ種別
        status (str): ジョブステータス
        started_at (str): 開始日時（ISO-8601）
        completed_at (Optional[str]): 完了日時（ISO-8601）
    """

    job_id: str = Field(..., description="ジョブID")
    job_type: str = Field(..., description="ジョブ種別")
    status: str = Field(..., description="ジョブステータス")
    started_at: str = Field(..., description="開始日時（ISO-8601）")
    completed_at: Optional[str] = Field(None, description="完了日時（ISO-8601）")


class BatchHistoryResponse(PaginationResponseSchema):
    """バッチ履歴一覧レスポンス.

    Attributes:
        items (List[BatchHistoryItem]): 履歴アイテム一覧
        count (int): アイテム総数
    """

    items: List[BatchHistoryItem] = Field(..., description="履歴アイテム一覧")
    count: int = Field(..., description="アイテム総数", ge=0)


class JobType(str, Enum):
    """バッチジョブの種別を表す列挙型."""

    SINGLE_STOCK = "SINGLE_STOCK"
    JPX_ALL_STOCKS = "JPX_ALL_STOCKS"
    STOCK_MASTER_UPDATE = "STOCK_MASTER_UPDATE"
    FUNDAMENTAL_DATA = "FUNDAMENTAL_DATA"
    EDINET_BALANCE_SHEET = "EDINET_BALANCE_SHEET"


class JobStatus(str, Enum):
    """バッチジョブの実行ステータスを表す列挙型."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchJobParams(BaseModel):
    """バッチジョブのパラメータスキーマ.

    Notes:
        代表的なフィールド(`symbol`, `timeframe`など)を定義し、その他は許容します。
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    symbol: Optional[str] = Field(None, description="Stock symbol (for single-stock jobs)")
    timeframe: Optional[str] = Field(None, description="Timeframe (e.g. 1d, 1m)")


class BatchExecutionBase(BaseModel):
    """BatchExecution の基底スキーマ.

    Attributes:
        job_type (JobType): ジョブ種別
        status (Optional[JobStatus]): ジョブステータス
        params (Optional[BatchJobParams]): ジョブパラメータ
        progress (Optional[float]): 進捗（0.0–100.0）
        success_count (Optional[int]): 成功件数
        failed_count (Optional[int]): 失敗件数
        error_message (Optional[str]): エラーメッセージ
        started_at (Optional[datetime]): 開始時刻
        finished_at (Optional[datetime]): 終了時刻
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    job_type: JobType = Field(..., description="Job type")
    status: Optional[JobStatus] = Field(None, description="Job status")
    params: Optional[BatchJobParams] = Field(None, description="Job parameters")
    progress: Optional[float] = Field(None, description="Progress (0.0–100.0)", ge=0.0, le=100.0)
    success_count: Optional[int] = Field(None, description="Number of successful items", ge=0)
    failed_count: Optional[int] = Field(None, description="Number of failed items", ge=0)
    error_message: Optional[str] = Field(None, description="Error message (if any)")
    started_at: Optional[datetime] = Field(None, description="Start time")
    finished_at: Optional[datetime] = Field(None, description="Finish time")


class BatchExecutionCreate(BaseRequestSchema, BatchExecutionBase):
    """ジョブ作成用スキーマ."""


class BatchExecutionUpdate(BaseModel):
    """ジョブ更新用スキーマ（部分更新）.

    Attributes:
        status (Optional[JobStatus]): ジョブステータス更新
        progress (Optional[float]): 進捗更新（0.0–100.0）
        success_count (Optional[int]): 成功件数更新
        failed_count (Optional[int]): 失敗件数更新
        error_message (Optional[str]): エラーメッセージ
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    status: Optional[JobStatus] = Field(None, description="Job status update")
    progress: Optional[float] = Field(
        None, description="Progress update (0.0–100.0)", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(
        None, description="Update number of successful items", ge=0
    )
    failed_count: Optional[int] = Field(None, description="Update number of failed items", ge=0)
    error_message: Optional[str] = Field(None, description="Error message (for update)")


class BatchExecutionResponse(BaseResponseSchema, BatchExecutionBase):
    """API レスポンス用の BatchExecution スキーマ.

    Note:
        `BaseResponseSchema` が `id`/`created_at`/`updated_at` を提供するため、
        追加フィールドは必要ありません。
    """


class JPXAllMultiSequenceRequest(BaseRequestSchema):
    """JPX全銘柄マルチ取得の順次実行リクエスト.

    Attributes:
        batch_size (Optional[int]): 一度に処理する銘柄数（デフォルト: 50）
    """

    batch_size: Optional[int] = Field(50, description="一度に処理する銘柄数", ge=1, le=200)


class TimeframeResult(BaseModel):
    """各タイムフレームの実行結果.

    Attributes:
        timeframe (str): タイムフレーム（1d/1m/1h）
        status (str): 実行ステータス
        success_count (int): 成功件数
        failed_count (int): 失敗件数
        error_message (Optional[str]): エラーメッセージ
        started_at (Optional[str]): 開始時刻（ISO-8601）
        finished_at (Optional[str]): 終了時刻（ISO-8601）
    """

    timeframe: str = Field(..., description="タイムフレーム")
    status: str = Field(..., description="実行ステータス")
    success_count: int = Field(0, description="成功件数", ge=0)
    failed_count: int = Field(0, description="失敗件数", ge=0)
    error_message: Optional[str] = Field(None, description="エラーメッセージ")
    started_at: Optional[str] = Field(None, description="開始時刻（ISO-8601）")
    finished_at: Optional[str] = Field(None, description="終了時刻（ISO-8601）")


class JPXAllMultiSequenceResponse(BaseResponseSchema):
    """JPX全銘柄マルチ取得の順次実行レスポンス.

    Attributes:
        job_id (str): ジョブID
        overall_status (str): 全体のステータス
        results (List[TimeframeResult]): 各タイムフレームの実行結果
    """

    job_id: str = Field(..., description="ジョブID")
    overall_status: str = Field(..., description="全体のステータス")
    results: List[TimeframeResult] = Field(
        default_factory=list, description="各タイムフレームの実行結果"
    )


class EdinetBalanceSheetRequest(BaseRequestSchema):
    """EDINET貸借対照表取得リクエスト.

    Attributes:
        start_date (str): 検索開始日（YYYY-MM-DD形式）
        end_date (str): 検索終了日（YYYY-MM-DD形式）
        progress_interval (Optional[int]): 進捗更新の間隔（処理ドキュメント数、デフォルト: 10）
        max_documents (Optional[int]): 処理する最大ドキュメント数（Noneの場合は全件処理）
    """

    start_date: str = Field(..., description="検索開始日（YYYY-MM-DD形式）")
    end_date: str = Field(..., description="検索終了日（YYYY-MM-DD形式）")
    progress_interval: Optional[int] = Field(
        10, description="進捗更新の間隔（処理ドキュメント数）", ge=1
    )
    max_documents: Optional[int] = Field(
        None, description="処理する最大ドキュメント数（Noneの場合は全件処理）", ge=1
    )


class EdinetBalanceSheetResponse(BaseResponseSchema):
    """EDINET貸借対照表取得レスポンス.

    Attributes:
        job_id (str): ジョブID（同期実行のため固定値）
        status (str): ジョブステータス
        total_documents (int): 検索された書類数
        processed_documents (int): 処理済み書類数
        saved_years (int): 保存された年度数
        failed_documents (int): 失敗した書類数
    """

    job_id: str = Field(..., description="ジョブID（同期実行のため固定値）")
    status: str = Field(..., description="ジョブステータス")
    total_documents: int = Field(0, description="検索された書類数", ge=0)
    processed_documents: int = Field(0, description="処理済み書類数", ge=0)
    saved_years: int = Field(0, description="保存された年度数", ge=0)
    failed_documents: int = Field(0, description="失敗した書類数", ge=0)


__all__ = [
    "SingleStockDataRequest",
    "JPXAllStocksRequest",
    "BatchJobResponse",
    "BatchJobProgress",
    "BatchJobStatusResponse",
    "BatchHistoryItem",
    "BatchHistoryResponse",
    "JobType",
    "JobStatus",
    "BatchJobParams",
    "BatchExecutionBase",
    "BatchExecutionCreate",
    "BatchExecutionUpdate",
    "BatchExecutionResponse",
    "JPXAllMultiSequenceRequest",
    "TimeframeResult",
    "JPXAllMultiSequenceResponse",
    "EdinetBalanceSheetRequest",
    "EdinetBalanceSheetResponse",
]
