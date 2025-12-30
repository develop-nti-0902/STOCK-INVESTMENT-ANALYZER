"""バッチAPI用のPydanticスキーマ定義

このモジュールは2つの役割を持ちます:
- Issue #140 に基づくバッチAPIで使用するリクエスト/レスポンススキーマ
- バッチ実行管理で使う列挙型 & 実行スキーマ（`JobType` / `BatchExecution*` 系）

両者を同一モジュールで提供し、APIレイヤからの参照を簡潔にします。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import (
    BaseRequestSchema,
    BaseResponseSchema,
    PaginationResponseSchema,
)


class SingleStockDataRequest(BaseRequestSchema):
    """単一銘柄のデータ取得リクエスト"""

    symbol: str = Field(..., description="銘柄コード")
    timeframe: str = Field(..., description="タイムフレーム")
    start_date: str = Field(..., description="開始日")
    end_date: str = Field(..., description="終了日")


class JPXAllStocksRequest(BaseRequestSchema):
    """JPX 全銘柄取得リクエスト"""

    timeframe: str = Field(..., description="タイムフレーム")
    start_date: str = Field(..., description="開始日")
    end_date: str = Field(..., description="終了日")
    market: Optional[str] = Field(None, description="市場区分")


class BatchJobResponse(BaseResponseSchema):
    """ジョブ作成レスポンス"""

    job_id: str = Field(..., description="ジョブID")
    job_type: str = Field(..., description="ジョブ種別")
    status: str = Field(..., description="ジョブステータス")
    estimated_completion: Optional[str] = Field(
        None, description="推定完了日時（ISO-8601）"
    )


class BatchJobProgress(BaseRequestSchema):
    processed: int = Field(..., description="処理済み件数", ge=0)
    total: int = Field(..., description="総件数", ge=0)
    percentage: float = Field(..., description="進捗率（0-100）")


class BatchJobStatusResponse(BaseResponseSchema):
    """ジョブステータスレスポンス（進捗情報含む）"""

    job_id: str = Field(..., description="ジョブID")
    job_type: str = Field(..., description="ジョブ種別")
    status: str = Field(..., description="ジョブステータス")
    progress: BatchJobProgress = Field(..., description="進捗情報")
    started_at: str = Field(..., description="開始日時（ISO-8601）")
    estimated_completion: Optional[str] = Field(
        None, description="推定完了日時（ISO-8601）"
    )


class BatchHistoryItem(BaseRequestSchema):
    job_id: str = Field(..., description="ジョブID")
    job_type: str = Field(..., description="ジョブ種別")
    status: str = Field(..., description="ジョブステータス")
    started_at: str = Field(..., description="開始日時（ISO-8601）")
    completed_at: Optional[str] = Field(
        None, description="完了日時（ISO-8601）"
    )


class BatchHistoryResponse(PaginationResponseSchema):
    """バッチ履歴一覧レスポンス"""

    items: List[BatchHistoryItem] = Field(..., description="履歴アイテム一覧")
    count: int = Field(..., description="アイテム総数", ge=0)


class JobType(str, Enum):
    SINGLE_STOCK = "SINGLE_STOCK"
    JPX_ALL_STOCKS = "JPX_ALL_STOCKS"
    STOCK_MASTER_UPDATE = "STOCK_MASTER_UPDATE"
    FUNDAMENTAL_DATA = "FUNDAMENTAL_DATA"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchJobParams(BaseModel):
    """バッチジョブのパラメータスキーマ

    代表的なフィールド(`symbol`, `timeframe`など)を定義し、その他は許容する設定にしています。
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    symbol: Optional[str] = Field(
        None, description="Stock symbol (for single-stock jobs)"
    )
    timeframe: Optional[str] = Field(
        None, description="Timeframe (e.g. 1d, 1m)"
    )


class BatchExecutionBase(BaseModel):
    """BatchExecution の基底スキーマ"""

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    job_type: JobType = Field(..., description="Job type")
    status: Optional[JobStatus] = Field(None, description="Job status")
    params: Optional[BatchJobParams] = Field(
        None, description="Job parameters"
    )
    progress: Optional[float] = Field(
        None, description="Progress (0.0–100.0)", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(
        None, description="Number of successful items", ge=0
    )
    failed_count: Optional[int] = Field(
        None, description="Number of failed items", ge=0
    )
    error_message: Optional[str] = Field(
        None, description="Error message (if any)"
    )
    started_at: Optional[datetime] = Field(None, description="Start time")
    finished_at: Optional[datetime] = Field(None, description="Finish time")


class BatchExecutionCreate(BaseRequestSchema, BatchExecutionBase):
    """ジョブ作成用スキーマ"""


class BatchExecutionUpdate(BaseModel):
    """ジョブ更新用スキーマ（部分更新を想定）"""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    status: Optional[JobStatus] = Field(None, description="Job status update")
    progress: Optional[float] = Field(
        None, description="Progress update (0.0–100.0)", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(
        None, description="Update number of successful items", ge=0
    )
    failed_count: Optional[int] = Field(
        None, description="Update number of failed items", ge=0
    )
    error_message: Optional[str] = Field(
        None, description="Error message (for update)"
    )


class BatchExecutionResponse(BaseResponseSchema, BatchExecutionBase):
    """APIレスポンス用スキーマ

    BaseResponseSchema が id/created_at/updated_at を提供するため、追加フィールド不要
    """


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
]
