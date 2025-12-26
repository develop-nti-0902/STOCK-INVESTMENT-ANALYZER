"""
バッチ実行関連のPydanticスキーマ

`JobType` / `JobStatus` Enum と `BatchExecution` 系のスキーマを定義します。
仕様: docs/architecture/layers/service_layer.md
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseRequestSchema, BaseResponseSchema


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
        None, description="銘柄コード（単一銘柄処理時）"
    )
    timeframe: Optional[str] = Field(None, description="時間軸（例: 1d, 1m）")


class BatchExecutionBase(BaseModel):
    """BatchExecution の基底スキーマ"""

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    job_type: JobType = Field(..., description="ジョブタイプ")
    status: JobStatus = Field(..., description="ジョブステータス")
    params: Optional[BatchJobParams] = Field(
        None, description="ジョブパラメータ"
    )
    progress: Optional[float] = Field(
        None, description="進捗（0.0〜100.0）", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(None, description="成功件数", ge=0)
    failed_count: Optional[int] = Field(None, description="失敗件数", ge=0)
    error_message: Optional[str] = Field(
        None, description="エラーメッセージ（発生時）"
    )
    started_at: Optional[datetime] = Field(None, description="開始時刻")
    finished_at: Optional[datetime] = Field(None, description="終了時刻")


class BatchExecutionCreate(BaseRequestSchema, BatchExecutionBase):
    """ジョブ作成用スキーマ"""

    # 作成時は status を省略可能（デフォルト PENDING をサーバー側でセット）
    status: Optional[JobStatus] = Field(
        None, description="初期ステータス（省略時はPENDING）"
    )


class BatchExecutionUpdate(BaseModel):
    """ジョブ更新用スキーマ（部分更新を想定）"""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    status: Optional[JobStatus] = Field(
        None, description="ジョブステータスの更新"
    )
    progress: Optional[float] = Field(
        None, description="進捗更新（0.0〜100.0）", ge=0.0, le=100.0
    )
    success_count: Optional[int] = Field(
        None, description="成功件数の更新", ge=0
    )
    failed_count: Optional[int] = Field(
        None, description="失敗件数の更新", ge=0
    )
    error_message: Optional[str] = Field(
        None, description="エラーメッセージ（更新時）"
    )


class BatchExecutionResponse(BaseResponseSchema, BatchExecutionBase):
    """APIレスポンス用スキーマ"""

    # BaseResponseSchema が id/created_at/updated_at を提供するため、追加フィールド不要
    pass


__all__ = [
    "JobType",
    "JobStatus",
    "BatchJobParams",
    "BatchExecutionBase",
    "BatchExecutionCreate",
    "BatchExecutionUpdate",
    "BatchExecutionResponse",
]
